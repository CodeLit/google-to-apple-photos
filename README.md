# 📸 Google to Apple Photos Metadata Synchronizer

> **⚠️ DISCLAIMER: Avoid using this library unless you have advanced needs!**
>
> For most users, use the official Google Takeout transfer tool instead:
> [https://takeout.google.com/takeout/transfer/custom/photos](https://takeout.google.com/takeout/transfer/custom/photos)
>
> Only use this library if you have advanced cases (e.g., deleting duplicates or other special workflows).


## 🎯 Objective

Fix incorrect photo and video metadata (especially dates, GPS coordinates, and titles) in files exported from Apple Photos by using accurate metadata from Google Takeout JSON files. This tool helps ensure your media files retain their original metadata when migrating from Google Photos to Apple Photos.

## ✨ Features

- **Metadata Synchronization**: Transfer dates, GPS coordinates, and titles from Google Takeout JSON files to media files
- **Smart Matching**: Match files by name or image hash for accurate pairing
- **Duplicate Detection**: Find and report duplicate files to avoid redundant imports
- **File Extension Correction**: Automatically detect and fix incorrect file extensions (e.g., HEIC files that are actually JPEG)
- **Detailed Logging**: Track all processed files and their metadata changes, including errors for failed updates
- **Parallel Processing**: Optimize performance with multi-threaded operations
- **Configurable Options**: Customize the synchronization process to fit your needs
- **Direct Apple Photos Import**: Import photos directly into Apple Photos after fixing metadata
- **Album Organization**: Preserve album structure from Google Takeout when importing to Apple Photos

Perfect for anyone migrating their photo library from Google Photos to Apple Photos who wants to preserve original metadata.

## 🪜 Steps Overview

### Simple Workflow (Recommended)

1. **Export from Google Photos**  
   Export photos and videos using **Google Takeout** into the `./old` folder.  
   Ensure `.json` metadata files are included alongside media files.

2. **Create New Directory**  
   Create an empty `./new` directory where files will be copied and processed.

3. **Run the Complete Workflow**  
   Execute the script without any arguments to run the complete workflow:
   ```bash
   python3 main.py
   ```
   
   This will automatically:
   - Copy missing files from `./old` to `./new`
   - Find and remove duplicates in `./new`
   - Apply metadata from Google Takeout JSON files to files in `./new`

### Advanced Workflow (Manual Steps)

1. **Export from Google Photos**  
   Export photos and videos using **Google Takeout** into the `./old` folder.  
   Ensure `.json` metadata files are included alongside media files.

2. **Backup (Optional)**  
   Save your current library into the `./archive` folder as a precaution.

3. **Export from Apple Photos or Copy from Old**  
   Either export photos from Apple Photos into `./new` folder ("Export Unmodified Originals"),  
   or copy files from `./old` to `./new` using:

   ```bash
   python3 main.py --copy-to-new
   ```

4. **Find Duplicates**  
   Identify duplicate files to avoid redundant processing:

   ```bash
   python3 main.py --find-duplicates-only
   ```

   Results will be saved to `duplicates.log`.

5. **Remove Duplicates**  
   Remove duplicate files based on the log:
   ```bash
   python3 main.py --remove-duplicates
   ```

6. **Sync Metadata**  
   Run the synchronization script to transfer metadata from `./old` to `./new`:
   ```bash
   python3 main.py --skip-copy --skip-duplicates
   ```
6. **Re-import into Apple Photos**  
   You can either manually import the files into Apple Photos, or use the built-in import feature:
   ```bash
   # Import photos after fixing metadata
   python3 main.py --import-to-photos
   
   # Import photos and organize them into albums based on Google Takeout structure
   python3 main.py --import-with-albums
   ```
   
   Alternatively, you can use the standalone import script:
   ```bash
   # Import all photos from the old directory
   python3 import_to_photos.py
   
   # Import with album organization
   python3 import_to_photos.py --with-albums
   
   # Import a specific file
   python3 import_to_photos.py --specific-file new/photo.jpg
   ```
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
  --failed-updates-log FAILED_UPDATES_LOG
                        Log file for failed metadata updates (default: failed_updates.log)
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

## 🔧 Recent Improvements

- **File Extension Correction**: Automatically detects and fixes incorrect file extensions (e.g., HEIC files that are actually JPEG)
- **Improved File Type Detection**: More robust detection of actual file types regardless of extension
- **Smart JPG/JPEG Handling**: Intelligently handles JPG/JPEG format variations without unnecessary conversions
- **Enhanced Error Handling**: Better handling of edge cases and error conditions with dedicated error logging
- **Optimized Logging**: Reduced log verbosity for common operations while preserving important information
- **Failed Updates Tracking**: Separate logging for files that fail metadata updates for easier troubleshooting

## 📊 Usage Examples

### Basic Usage

The most common workflow is to run the script without any options:

```bash
python3 main.py
```

This will process all files in the default directories (`./old` and `./new`).

### Copying Files from Old to New

If you want to copy files from the `./old` directory to `./new` before processing:

```bash
python3 main.py --copy-to-new
```

### Dry Run

To test the process without making any changes to files:

```bash
python3 main.py --dry-run
```

### Limiting the Number of Files

To process only a specific number of files (useful for testing):

```bash
python3 main.py --limit 100
```

### Using Custom Directories

If your files are in different locations:

```bash
python3 main.py --old-dir /path/to/google/takeout --new-dir /path/to/apple/exports
```

## 🤝 Contributing

Contributions are welcome! If you'd like to improve this tool, please feel free to submit a pull request or open an issue.
