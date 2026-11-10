#!/usr/bin/env bash
set -euo pipefail

version=v1.0.4
base_url=https://workbench-cli.oss-cn-hangzhou.aliyuncs.com/releases/${version}
archive=workbench-linux-amd64.tar.gz
staging=$(mktemp -d)
trap 'rm -rf "$staging"' EXIT
curl --fail --silent --show-error --location --retry 3 --max-time 120 \
    "${base_url}/${archive}" -o "${staging}/${archive}"
curl --fail --silent --show-error --location --retry 3 --max-time 60 \
    "${base_url}/checksums.sha256" -o "${staging}/checksums.sha256"
expected=$(awk -v name="$archive" '$2 == name {print $1}' "${staging}/checksums.sha256")
[[ $expected =~ ^[a-f0-9]{64}$ ]] || { echo 'Missing or invalid official checksum' >&2; exit 1; }
actual=$(sha256sum "${staging}/${archive}" | cut -d ' ' -f 1)
[[ $actual == "$expected" ]] || { echo 'Workbench checksum mismatch' >&2; exit 1; }
tar -xzf "${staging}/${archive}" -C "$staging"
install -d "${RUNNER_TEMP}/workbench-bin"
install -m 0755 "${staging}/workbench-linux-amd64/workbench" "${RUNNER_TEMP}/workbench-bin/workbench"
echo "${RUNNER_TEMP}/workbench-bin" >> "$GITHUB_PATH"
"${RUNNER_TEMP}/workbench-bin/workbench" version
