import os
import subprocess
import json
from datetime import datetime
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import hashlib

AUDIO_EXTENSIONS = (".flac", ".mp3", ".wav", ".m4a", ".aac", ".ogg")
TOLERANCE_SECONDS = 0.5
OUTPUT_FILE = "scan_report.md"

GLOBAL_PATH = Path(__file__).resolve().parent
CHECK_LOG = GLOBAL_PATH / "check_log.json"

def normalize(p):
    return os.path.normcase(os.path.normpath(p))

# any albums that are actually meant to be such a large file size, you can set to be ignored by the script. add here as you encounter them.
IGNORE_SIZE_PATHS = [
    # r"D:\Music\Sam Cooke\Mr. Soul (1963)"
]

IGNORE_SIZE_PATHS = set(normalize(p) for p in IGNORE_SIZE_PATHS)

MTIME_TOLERANCE = 60

def is_ignored(path):
    for ignore in IGNORE_SIZE_PATHS:
        if path == ignore or path.startswith(ignore + os.sep):
            return True
    return False

def load_log(mpath):
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

def process_hash(full_path, old_manifest):
    rel_path = os.path.relpath(full_path, GLOBAL_PATH)
    stat = os.stat(full_path)

    size = stat.st_size
    mtime = int(stat.st_mtime)

    old_entry = old_manifest["files"].get(rel_path)

    if old_entry and old_entry["size"] == size and abs(old_entry["mtime"] - mtime) <= MTIME_TOLERANCE:
        return rel_path, old_entry, "skipped"

    return rel_path, {
        "size": size,
        "mtime": mtime,
    }, "changed"

def run_subprocess(cmd):
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

def get_metadata_duration(file_path):
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        file_path
    ]

    result = run_subprocess(cmd)

    if not result.stdout:
        return None

    try:
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return None

def get_decoded_duration(file_path):
    cmd = [
        "ffmpeg",
        "-vn",
        "-i", file_path,
        "-f", "null",
        "-"
    ]

    result = run_subprocess(cmd)

    text = result.stderr.replace("\r", "\n")
    matches = re.findall(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", text)

    if matches:
        h, m, s = matches[-1]
        return int(h) * 3600 + int(m) * 60 + float(s)
    
    return None

def process_file(full_path, verified_log):
    rel_path, hash_entry, hash_status = process_hash(
        full_path,
        verified_log
    )
    norm_path = normalize(full_path)
    
    if hash_status == "skipped":
        return ("verified_skip", rel_path, hash_entry)


    time.sleep(0.01)
    meta_duration = get_metadata_duration(full_path)
    decoded_duration = get_decoded_duration(full_path)

    if meta_duration is None or decoded_duration is None:
        return None

    diff = abs(meta_duration - decoded_duration)

    if diff > TOLERANCE_SECONDS:
        return ("problem", full_path, meta_duration, decoded_duration, diff)
    
    file_hash = hash_file(full_path)

    file_size_kb = (os.path.getsize(full_path))/1024
    file_kbps = (file_size_kb * 8)/meta_duration

    if file_kbps > 5000 and not is_ignored(norm_path):
        return ("large", full_path, meta_duration, file_size_kb)
    
    return (
        "verified",
        rel_path,
        {
            "size": hash_entry["size"],
            "mtime": hash_entry["mtime"],
            "hash": file_hash,
            "verified": True,
            "meta_duration": meta_duration,
            "decoded_duration": decoded_duration,
            "last_checked": str(datetime.now())
        }
    )

def scan_folder(folder, verified_log):
    problem_files = []
    large_files = []
    verified_files = []

    all_files = []

    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(AUDIO_EXTENSIONS):
                full_path = os.path.join(root, file)
                all_files.append(full_path)

    total_files = len(all_files)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_file, f, verified_log): f for f in all_files}

        for i, future in enumerate(as_completed(futures)):
            result = future.result()

            if result:
                status = result[0]

                if status == "verified_skip":
                    _, rel_path, entry = result
                    verified_log["files"][rel_path] = entry
                    verified_files.append(rel_path)
                
                elif status == "verified":
                    _, rel_path, entry = result
                    verified_log["files"][rel_path] = entry
                    verified_files.append(rel_path)

            print(f"[{i+1}/{len(all_files)}] Done: {futures[future]}")

            if result:
                if result[0] == "problem":
                    _, path, meta, decoded, diff = result
                    index = len(problem_files) + 1
                    problem_files.append((index, path, meta, decoded, diff))
                elif result[0] == "large":
                    _, path, meta, size = result
                    index = len(large_files) + 1
                    large_files.append((index, path, meta, size))

    write_report(folder, total_files, problem_files, large_files)

def write_report(folder, total_files, problem_files, large_files):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Audio Duration Scan Report\n\n")
        f.write(f"**Scanned Folder:** `{folder}`  \n")
        f.write(f"**Scan Date:** {datetime.now()}  \n")
        f.write(f"**Total Files Checked:** {total_files}  \n")
        f.write(f"**Files With Significant Duration Mismatch:** {len(problem_files)}  \n")
        f.write(f"**Files With Significant File Size:** {len(large_files)} \n\n")
        f.write("---\n\n")

        if problem_files:
            for index, file, meta, decoded, diff in problem_files:
                f.write(f"## `{index}` ✗ {os.path.basename(file)}\n")
                f.write(f"- **Full Path:** `{file}`\n")
                f.write(f"- **Metadata Duration:** {meta:.3f} sec\n")
                f.write(f"- **Decoded Duration:** {decoded:.3f} sec\n")
                f.write(f"- **Difference:** {diff:.3f} sec\n\n")
        
        if large_files:
            for index, file, meta, file_size_kb in large_files:
                f.write(f"## `{index}` ✗ {os.path.basename(file)}\n")
                f.write(f"- **Full Path:** `{file}`\n")
                f.write(f"- **Metadata Duration:** {meta:.3f} sec \n")
                f.write(f"- **File Size:** {file_size_kb} \n\n")


        if not problem_files or not large_files:
            f.write("✓ No significant issues found.\n")

    print(f"\nReport written to {OUTPUT_FILE}")

def save_log(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    verified_log = load_log(CHECK_LOG)

    scan_folder(GLOBAL_PATH, verified_log) #os.path.dirname(os.path.abspath(__file__))

    save_log(verified_log, CHECK_LOG)