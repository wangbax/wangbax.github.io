#!/usr/bin/env bash
# Publish a verified archive. Nginx reads the new symlink without a restart.
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo 'Usage: publish.sh RELEASE_ID ARCHIVE_SHA256' >&2
    exit 2
fi
release_id=$1
archive_sha256=$2
if [[ ! $release_id =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$ ]]; then
    echo 'Invalid release ID' >&2
    exit 2
fi
if [[ ! $archive_sha256 =~ ^[a-f0-9]{64}$ ]]; then
    echo 'Invalid SHA256 checksum' >&2
    exit 2
fi

site_base=/var/www/iwyatt
archive=/var/tmp/iwyatt-${release_id}.tar.gz
release_dir=${site_base}/releases/${release_id}
if [[ -e $release_dir || -L $release_dir ]]; then
    echo 'Release already exists; refusing to overwrite it' >&2
    exit 1
fi
if [[ -e ${site_base}/current && ! -L ${site_base}/current ]]; then
    echo 'The current site path is not a managed symlink' >&2
    exit 1
fi
if [[ -e ${site_base}/previous && ! -L ${site_base}/previous ]]; then
    echo 'The previous site path is not a managed symlink' >&2
    exit 1
fi
if [[ $(sha256sum "$archive" | cut -d ' ' -f 1) != "$archive_sha256" ]]; then
    echo 'Archive checksum mismatch' >&2
    exit 1
fi
nginx -t

install -d -m 755 "$site_base" "${site_base}/releases" "$release_dir"
tar --extract --gzip --file "$archive" --directory "$release_dir" --no-same-owner --no-same-permissions
test -f "${release_dir}/index.html"
test -f "${release_dir}/404.html"
test -f "${release_dir}/css/main.css"
find "$release_dir" -type d -exec chmod 755 {} +
find "$release_dir" -type f -exec chmod 644 {} +
if command -v restorecon >/dev/null 2>&1; then
    restorecon -RF "$site_base"
fi

if [[ -L ${site_base}/current ]]; then
    previous_target=$(readlink "${site_base}/current")
    ln -s "$previous_target" "${site_base}/.previous-${release_id}"
    mv -Tf "${site_base}/.previous-${release_id}" "${site_base}/previous"
fi
ln -s "releases/${release_id}" "${site_base}/.current-${release_id}"
mv -Tf "${site_base}/.current-${release_id}" "${site_base}/current"
echo "Published ${release_id} to ${site_base}/current"
