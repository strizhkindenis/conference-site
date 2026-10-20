#!/usr/bin/env bash

set -euo pipefail

host="conference.spbau"
staging_dir="$(mktemp -d)"

cleanup() {
    rm -rf "$staging_dir"
}

trap cleanup EXIT

mkdir -p "$staging_dir/alembic/versions" "$staging_dir/src"
cp -a alembic/versions/. "$staging_dir/alembic/versions/"
cp -a src/. "$staging_dir/src/"

find "$staging_dir" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$staging_dir" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

ssh "$host" 'mkdir -p /app/alembic/versions /app/src'
scp -r "$staging_dir/alembic/versions/." "$host:/app/alembic/versions/"
scp -r "$staging_dir/src/." "$host:/app/src/"
