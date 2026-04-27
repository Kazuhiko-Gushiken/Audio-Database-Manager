# Audio Database Manager

This set of scripts (and future all-in-one program) is meant to allow you to manage your audio (probably music) database. It will check the integrity of your files, flag stupidly re-encoded files, as well as allow you quick syncing with a portable storage medium.

## Audio Database Verifier:

The `check.py` script is meant to verify the integrity of your local audio library. It checks for two main this (possibly more in the future):
- It compares the metadata's duration statistic with the actual decoded duration using FFMPEG. If the decoded duration is beyond `0.5s` of the metadata's duration (which the metadata's should be the actual duration of the audio), then it will flag it. Sometimes an audio file can be corrupted and the decoded duration is far smaller than the metadata. During playback, the audio will stop prematurely, mid-song.
- It compares the total bitrate of the audio file to a strict maximum of `5000 Kbps`. If the bitrate is beyond this, it will be flagged. Sometimes people like to re-encode an audio file at a way higher bit-depth and/or sample rate than the original was, causing unnecessarily large file sizes. By flagging them, you can search for and replace with properly encoded audio files. Now, some audio files may be actually a high bit-rate and/or sample rate, thus, you can add to the list of ignored file paths in the script (on line 17) so the script will pass by them and not flag the album/file.

All flags will be output into a `scan_report.md` file, stating important information such as:
- File Name
- Full Path
- Metadata Duration
- Decoded Duration
- Difference
- File Size

## Library Hasher:

The `hash_source.py` and `hash_dest.py` are both meant to hash your library in both the source directory and destination directory. Only one is setup for multi-threaded processing. They are essentially the same file, but with different manifest paths. In the future, the script will implement arguments to choose source or destination to compact it into a single script.

It produces a manifest that logs the file name, size, modified time, and a `sha256` hash. The manifest helps with two things:
- It is a single file that catalogues your entire library and their "fingerprints." The hash script will use the manifest to skip already hashed files (comparing the manifest to the file's size and modification time) to save time.
- It helps sync your local global library with your portable library (in various possible audio players) without needing to delete or copy any unnecessary files. It will compare with the portable library's manifest to decide which files need to be updated, which files are new and need to be copied over, and which files need to be removed from the portable library. This helps mitigate the bottleneck of slow MicroSD card transfer speeds.

## Library Sync:

The `sd_sync.py` script does what the second bullet point of the block of text above says. It syncs your local global library with your portable library in an efficient manner. It is set to ignore all script, manifest, and report files so you can keep the script files inside of your library paths.

## How to use:

### Audio Database Verifier:

Place the `check.py` file into two locations:
- Global Library Directory Path (e.g. `D:/Music/Library/`)
- Download Directory Path (e.g. `D:/Music/Downloads/`)

Run the check script for your global library once. Use the check script in your downloads path to check file integrity before moving to the library, to avoid needing to scan the entire library *again*. Since the check script needs to decode the each file, it may take a long time for large libraries.

### Library Hasher:

Place the `hash_source.py` file into the Global Library Directory Path and run it. It will hash your entire library. This is fine to run again when you add new files, as it will only re-hash new/changed files.

Place the `hash_dest.py` file into the Portable Library Directory Path (e.g. `G:/Music/Portable`) and run it *once*. Each time you use the sync script, it will update the destination's manifest accordingly.

### Library Sync:

Place the `sd_sync.py` file into the Global Library Directory Path. Open the script and on line `7` and line `10`, enter the absolute path for the Portable Library Directory and the Portable Library Manifest respectively. You can run this whenever you want to sync any new or changed files (metadata) to your portable storage medium.

## TODO:

- [ ] Combine hash scripts into one.
- [ ] Make default action of combined hash script be hashing the destination, with an optional argument `-d` to hash the destination.
- [ ] Improve the reliability of the `check.py` script. Some audio files spit out false negatives in terms of decoded durations, despite audio players such as Windows Media Player and VLC properly playings the audio.
- [ ] Implement all scripts into an optional UI for easier use by the non-technologically inclined.