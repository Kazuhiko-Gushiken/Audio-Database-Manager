import os
import json
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse

# Input paths as you'd like. The string below means "directory the script is in".
# It defaults that the script is in the global library directory, and the portable library directory needs to be added.
# Path(__file__).resolve().parent

GLOBAL_LIBRARY_PATH = Path(__file__).resolve().parent
GLOBAL_MANIFEST_PATH = GLOBAL_LIBRARY_PATH / "library_manifest.json"
PORTABLE_LIBRARY_PATH = Path(r"") # Needs Path!!
PORTABLE_MANIFEST_PATH = PORTABLE_LIBRARY_PATH / "sd_manifest.json"

IGNORE_FILES = {
    "library_manifest.json",
    "sd_manifest.json",
    "hash_source.py",
    "hash_dest.py",
    "hash.py",
    "sd_sync.py",
    "check.py",
    "check_log.json",
    "scan_report.md",
    ".nomedia"
}

MTIME_TOLERANCE = 60

def load_manifest(mpath):
    if mpath.exists():
        with open(mpath, "r") as f:
            return json.load(f)
    return {"files": {}}

def hash_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()

# worker function
def process_file(full_path, old_manifest, dpath):
    rel_path = full_path.relative_to(dpath).as_posix()
    stat = full_path.stat()

    size = stat.st_size
    mtime = int(stat.st_mtime)

    old_entry = old_manifest["files"].get(rel_path)

    if old_entry and old_entry["size"] == size and abs(old_entry["mtime"] - mtime) <= MTIME_TOLERANCE:
        return rel_path, old_entry, "skipped"
    
    file_hash = hash_file(full_path)

    return rel_path, {
        "size": size,
        "mtime": mtime,
        "hash": file_hash,
    }, "hashed"

def scan_library(dest):
    if dest:
        USE_PATH = PORTABLE_LIBRARY_PATH
        USE_MANIFEST = PORTABLE_MANIFEST_PATH
    else:
        USE_PATH = GLOBAL_LIBRARY_PATH
        USE_MANIFEST = GLOBAL_MANIFEST_PATH

    old_manifest = load_manifest(USE_MANIFEST)
    new_manifest = {"files": {}}

    file_list = []

    for root, _, files in os.walk(USE_PATH):
        for file in files:
            full_path = Path(root) / file

            if full_path.name in IGNORE_FILES:
                continue
            
            file_list.append(full_path)

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(lambda p: process_file(p, old_manifest, USE_PATH), file_list)

        for i, (rel_path, data, status) in enumerate(results, start=1):
            new_manifest["files"][rel_path] = data
            if status == "skipped":
                print(f"[{i}/{len(file_list)}] Skipped (unchanged): {rel_path}")
            else:
                print(f"[{i}/{len(file_list)}] Hashed: {rel_path}")

    return new_manifest

def save_manifest(data, mpath):
    with open(mpath, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--destination", action="store_true")
    args = parser.parse_args()
    dest = args.destination

    manifest = scan_library(dest)

    if dest:
        mpath = PORTABLE_MANIFEST_PATH
    else:
        mpath = GLOBAL_MANIFEST_PATH

    save_manifest(manifest, mpath)
    print("Done.")