import shutil
import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
DEST = Path(r"") # absolute path to destination root

SRC_MANIFEST = SOURCE / "library_manifest.json"
DST_MANIFEST = Path(r"") # absolute path to destination manifest "sd_manifest.json"

IGNORE_FILES = {
    "library_manifest.json",
    "sd_manifest.json",
    "hash_source.py",
    "hash_dest.py",
    "hash.py",
    "sd_sync.py",
    "check.py",
    "scan_report.md",
    "check_log.json",
    ".nomedia"
}

IGNORE_EXTENSIONS = {
    ".mp4",
    ".description",
    ".vtt",
}

def load_json(path):
    if not path.exists():
        return {"files": {}}
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def sync():
    src = load_json(SRC_MANIFEST)
    dst = load_json(DST_MANIFEST)

    src_files = src["files"]
    dst_files = dst["files"]

    for rel_path, info in src_files.items():
        path = Path(rel_path)

        if path.name in IGNORE_FILES or path.suffix in IGNORE_EXTENSIONS or path.name.endswith(".metadata.json"):
            continue

        src_file = SOURCE / rel_path
        dst_file = DEST / rel_path

        if rel_path not in dst_files:
            print(f"NEW: {rel_path}")
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)

        elif dst_files[rel_path]["hash"] != info["hash"]:
            print(f"UPDATED: {rel_path}")
            shutil.copy2(src_file, dst_file)

    for rel_path in dst_files:
        path = Path(rel_path)

        if path.name in IGNORE_FILES or path.suffix in IGNORE_EXTENSIONS or path.name.endswith(".metadata.json"):
            continue

        if rel_path not in src_files:
            print(f"DELETE: {rel_path}")
            (DEST / rel_path).unlink(missing_ok=True)

    save_json(DST_MANIFEST, src)

if __name__ == "__main__":
    sync()