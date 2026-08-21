"""
push_ota.py — publish a new build to the VDS so every client picks it up.

This script previously pushed to a Firebase Realtime Database
(bogazicidersyonetim-default-rtdb) that the application had already stopped
talking to, while the client polled the VDS for updates. The two halves were never
connected, so publishing an update did nothing at all.

Usage:

    python push_ota.py --version 3.0.1 --build 301 \
        --url https://.../Chenki_3.0.1.zip \
        --package dist/Chenki_3.0.1.zip \
        --notes "Duplicate versions fixed, drag-to-folder works"

--package is optional but strongly recommended: its SHA-256 is published with the
manifest and the client refuses any download that does not match, which is what
stops anything that can answer the URL from shipping code to your users.
"""
import argparse
import getpass
import hashlib
import os
import sys

import requests

DEFAULT_API = os.environ.get("CHENKI_API_URL", "http://213.142.159.36")


def sha256_of(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish an update manifest to the VDS.")
    parser.add_argument("--version", required=True, help="Human-readable version, e.g. 3.0.1")
    parser.add_argument("--build", type=int, required=True,
                        help="Integer build number. MUST be higher than the running clients'.")
    parser.add_argument("--url", required=True, help="Download URL for the package")
    parser.add_argument("--package", help="Local package file, hashed and published for verification")
    parser.add_argument("--notes", default="", help="Release notes shown to the user")
    parser.add_argument("--mandatory", action="store_true", help="Prompt on every launch until applied")
    parser.add_argument("--api", default=DEFAULT_API, help=f"API base URL (default {DEFAULT_API})")
    parser.add_argument("--email", default="sehersanli@chenki.net", help="Admin account")
    args = parser.parse_args()

    api = args.api.rstrip("/")

    sha = ""
    if args.package:
        if not os.path.exists(args.package):
            print(f"error: package not found: {args.package}")
            return 1
        sha = sha256_of(args.package)
        print(f"package sha256: {sha}")
    else:
        print("warning: no --package given, so the client cannot verify the download.")

    password = os.environ.get("BGZ_ADMIN_PASSWORD") or getpass.getpass(f"Password for {args.email}: ")

    try:
        login = requests.post(
            f"{api}/auth/login",
            data={"username": args.email, "password": password},
            timeout=15,
        )
    except Exception as exc:
        print(f"error: cannot reach {api}: {exc}")
        return 1

    if login.status_code != 200:
        print(f"error: login failed (HTTP {login.status_code}): {login.text}")
        return 1

    token = login.json()["access_token"]

    resp = requests.post(
        f"{api}/api/updates",
        json={
            "version": args.version,
            "build": args.build,
            "notes": args.notes,
            "url": args.url,
            "sha256": sha,
            "mandatory": bool(args.mandatory),
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )

    if resp.status_code != 200:
        print(f"error: publish failed (HTTP {resp.status_code}): {resp.text}")
        return 1

    print(f"published: {resp.json()}")
    print("Clients will offer this update on their next check (startup, then hourly).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
