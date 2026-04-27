import os
import json
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

LIBRARY_PATH = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(LIBRARY_PATH, "library_manifest.json")

IGNORE_FILES = {
    "library_manifest.json",
    "sd_manifest.json",
    "hash_source.py",
    "hash_dest.py",
    "sd_sync.py",
    "check.py"
    "scan_report.md"
}

def load_manifest():
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r") as f:
            return json.load(f)
    return {"files": {}}

def hash_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()

# worker function
def process_file(full_path, old_manifest):
    rel_path = full_path.relative_to(LIBRARY_PATH).as_posix()
    stat = full_path.stat()

    size = stat.st_size
    mtime = int(stat.st_mtime)

    old_entry = old_manifest["files"].get(rel_path)

    if old_entry and old_entry["size"] == size and old_entry["mtime"] == mtime:
        return rel_path, old_entry, "skipped"
    
    file_hash = hash_file(full_path)

    return rel_path, {
        "size": size,
        "mtime": mtime,
        "hash": file_hash,
    }, "hashed"

def scan_library():
    old_manifest = load_manifest()
    new_manifest = {"files": {}}

    file_list = []

    for root, _, files in os.walk(LIBRARY_PATH):
        for file in files:
            full_path = Path(root) / file

            if full_path.name in IGNORE_FILES:
                continue
            
            file_list.append(full_path)

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(lambda p: process_file(p, old_manifest), file_list)

        for rel_path, data, status in results:
            new_manifest["files"][rel_path] = data
            if status == "skipped":
                print(f"Skipped (unchanged): {rel_path}")
            else:
                print(f"Hashed: {rel_path}")

    return new_manifest\

def save_manifest(data):
    with open(MANIFEST_PATH, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    manifest = scan_library()
    save_manifest(manifest)
    print("Done.")