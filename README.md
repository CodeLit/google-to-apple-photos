# 📸 Google to Apple Photos Metadata Synchronizer

## 🎯 Objective

Transfer accurate photo and video metadata (especially creation dates, GPS coordinates, and titles) from Google Takeout export to files for clean import into Apple Photos.

## ✨ Features

- **Metadata Synchronization**: Transfer dates, GPS coordinates, and titles from Google Takeout JSON files to media files
- **Smart Matching**: Match files by name or image hash for accurate pairing
- **Duplicate Detection**: Find and report duplicate files to avoid redundant imports
- **Detailed Logging**: Track all processed files and their metadata changes
- **Parallel Processing**: Optimize performance with multi-threaded operations

## 🪜 Steps Overview

1. **Export from Google Photos**  
   Export photos and videos using **Google Takeout** into the `./old` folder.  
   Ensure `.json` metadata files are included alongside media files.

2. **Backup (Optional)**  
   Save your current library into the `./archive` folder as a precaution.

3. **Export from Apple Photos** (или копирование из old)  
   Export all photos and videos from **Apple Photos Library** into the `./new` folder.  
   Use "Export Unmodified Originals" in Photos app for best results.  
   Alternatively, use the `--copy-to-new` option to copy files from `./old` to `./new`:
   ```bash
   python3 main.py --copy-to-new
   ```

4. **Find Duplicates (Optional)**  
   Identify duplicate files in your export to avoid redundant processing:
   ```bash
   python3 main.py --find-duplicates-only
   ```
   Results will be saved to `duplicates.log`.

5. **Sync Metadata**  
   Run the synchronization script to transfer metadata from `./old` to `./new`:
   ```bash
   python3 main.py
   ```
   
6. **Re-import into Apple Photos**  
   Import updated files from `./new` back into **Apple Photos**.  
   Apple Photos will read and use the corrected metadata during import.

## 🛠️ Command Line Options

```
usage: main.py [-h] [--dry-run] [--old-dir OLD_DIR] [--new-dir NEW_DIR] [--limit LIMIT] [--verbose] [--quiet] [--no-hash-matching] [--similarity SIMILARITY] [--find-duplicates-only] [--processed-log PROCESSED_LOG] [--copy-to-new]

Synchronize metadata from Google Takeout to Apple Photos exports

options:
  -h, --help            show this help message and exit
  --dry-run             Perform a dry run without modifying any files
  --old-dir OLD_DIR     Directory with Google Takeout files (default: old)
  --new-dir NEW_DIR     Directory with Apple Photos exports (default: new)
  --limit LIMIT         Limit processing to specified number of files
  --verbose, -v         Enable verbose output
  --quiet, -q           Suppress warning messages about missing files
  --no-hash-matching    Disable image hash matching (faster but less accurate)
  --similarity SIMILARITY
                        Similarity threshold for image matching (0.0-1.0, default: 0.98)
  --find-duplicates-only
                        Only find and report duplicates without updating metadata
  --processed-log PROCESSED_LOG
                        Log file for processed files (default: processed_files.log)
  --copy-to-new        Copy media files from old directory to new directory before processing
```

## 📋 Requirements

- Python 3.6 or higher
- exiftool (external dependency)
- Optional: Pillow and imagehash for improved image matching

## 📝 Installation

1. Clone this repository
2. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
3. Install exiftool (if not already installed):
   - macOS: `brew install exiftool`
   - Linux: `apt-get install exiftool` or equivalent
   - Windows: Download from [exiftool.org](https://exiftool.org)
