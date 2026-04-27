import os
import json
import hashlib
from pathlib import Path

LIBRARY_PATH = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(LIBRARY_PATH, "sd_manifest.json")

IGNORE_FILES = {
    "library_manifest.json",
    "sd_manifest.json",
    "hash_source.py",
    "hash_dest.py",
    "sd_sync.py",
    "check.py"
    "scan_report.md"
}


def hash_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def scan_library():
    manifest = {"files": {}}

    for root, _, files in os.walk(LIBRARY_PATH):
        for file in files:
            full_path = Path(root) / file

            if full_path.name in IGNORE_FILES:
                continue

            rel_path = full_path.relative_to(LIBRARY_PATH).as_posix()

            stat = full_path.stat()

            manifest["files"][rel_path] = {
                "size": stat.st_size,
                "mtime": int(stat.st_mtime),
                "hash": hash_file(full_path),
            }

            print(f"Indexed: {rel_path}")

    return manifest


def save_manifest(data):
    with open(MANIFEST_PATH, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    manifest = scan_library()
    save_manifest(manifest)
    print("Done.")