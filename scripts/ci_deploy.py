#!/usr/bin/env python3
"""Publish from GitHub Actions using an OIDC-issued, temporary Workbench profile."""

import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener


def remote(instance, region, command):
    result = subprocess.run(
        ["workbench", "exec", "--instance-id", instance, "--region", region,
         "--command", command, "--timeout", "90", "--output", "json"],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError("Workbench failed: " + (result.stderr or result.stdout))
    data = json.loads(result.stdout)
    if data.get("exit_code") != 0:
        raise RuntimeError("Remote command failed: " + data.get("stderr", ""))
    print(data.get("stdout", data.get("output", "")), flush=True)


def verify_site(origin, expected_index):
    checks = [("/healthz", 200, b"ok"), ("/", 200, expected_index),
              ("/css/site.css", 200, None), ("/css/pages.css", 200, None), ("/css/theme.css", 200, None), ("/js/theme.js", 200, None),
              ("/js/site.js", 200, None), ("/js/planet.js", 200, None), ("/search.xml", 200, None),
              ("/does-not-exist", 404, None), ("/.git/config", 403, None)]
    for path, status, expected in checks:
        for attempt in range(3):
            try:
                try:
                    response = build_opener(ProxyHandler({})).open(origin + path, timeout=15)
                except HTTPError as error:
                    response = error
                with response:
                    content = response.read()
                    if response.code != status or (expected is not None and content != expected):
                        raise RuntimeError(f"Unexpected response for {path}: HTTP {response.code}")
                break
            except (URLError, TimeoutError, RuntimeError):
                if attempt == 2:
                    raise
                time.sleep(3)
        print(f"Verified {path}: HTTP {status}", flush=True)


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise SystemExit("Deployment is restricted to GitHub Actions on main")
    origin = os.environ["SITE_URL"].rstrip("/")
    instance, region = os.environ["ECS_INSTANCE_ID"], os.environ["ECS_REGION"]
    release_id = "gha-{}-{}-{}".format(os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"], os.environ["GITHUB_SHA"][:12])
    archive = Path(".release/site.tar.gz")
    subprocess.run([sys.executable, "scripts/package_site.py", "--site-url", origin], check=True)
    subprocess.run([sys.executable, "scripts/check_site.py", str(archive)], check=True)

    profile = {
        "mode": "StsToken", "region": region,
        "access_key_id": os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
        "access_key_secret": os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
        "sts_token": os.environ["ALIBABA_CLOUD_SECURITY_TOKEN"],
    }
    config = Path.home() / ".workbench/config.json"
    config.parent.mkdir(mode=0o700, exist_ok=True)
    with os.fdopen(os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
        json.dump({"current": "github", "profiles": {"github": profile}}, stream)
    try:
        remote_archive = f"/var/tmp/iwyatt-{release_id}.tar.gz"
        remote_script = f"/var/tmp/iwyatt-{release_id}-publish.sh"
        remote(instance, region, " && ".join(f"test ! -e {shlex.quote(path)} && test ! -L {shlex.quote(path)}" for path in [remote_archive, remote_script]))
        for source, target in [(str(archive), remote_archive), ("deploy/publish.sh", remote_script)]:
            subprocess.run(["workbench", "upload", source, target, "--instance-id", instance, "--region", region], check=True)
        archive_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        script_digest = hashlib.sha256(Path("deploy/publish.sh").read_bytes()).hexdigest()
        command = "echo {} | sha256sum -c - && bash {} {} {}".format(
            shlex.quote(script_digest + "  " + remote_script), shlex.quote(remote_script),
            shlex.quote(release_id), shlex.quote(archive_digest),
        )
        remote(instance, region, command)
        with tarfile.open(archive, "r:gz") as package:
            expected_index = package.extractfile("index.html").read()
        verify_site(origin, expected_index)
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
            summary.write(f"Published `{release_id}` to [{origin}]({origin}). Public HTTP checks passed." + chr(10))
    finally:
        config.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
