# 📚 Google to Apple Photos Metadata Synchronizer - Usage Guide

This document provides detailed information about all available command-line options and how to use them effectively.

## 🔧 Command-Line Options

### Basic Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Perform a dry run without modifying any files |
| `--old-dir DIR` | Directory with Google Takeout files (default: old) |
| `--new-dir DIR` | Directory with Apple Photos exports (default: new) |
| `--limit N` | Limit processing to specified number of files |
| `--verbose`, `-v` | Enable verbose output |
| `--quiet`, `-q` | Suppress warning messages about missing files |

### Matching and Detection Options

| Option | Description |
|--------|-------------|
| `--no-hash-matching` | Disable image hash matching (faster but less accurate) |
| `--similarity FLOAT` | Similarity threshold for image matching (0.0-1.0, default: 0.98) |
| `--find-duplicates-only` | Only find and report duplicates without updating metadata |
| `--find-duplicates-by-name` | Find duplicates by checking for files with the same base name but with suffix |
| `--duplicates-log FILE` | Log file for duplicates (default: logs/duplicates.log) |
| `--name-duplicates-log FILE` | Log file for name-based duplicates (default: name_duplicates.log) |

### File Management Options

| Option | Description |
|--------|-------------|
| `--copy-to-new` | Copy files from old directory to new directory before processing |
| `--remove-duplicates` | Remove duplicate files in the new directory based on duplicates.log |
| `--rename-files` | Rename files by removing "(1)" from filenames |
| `--rename-suffix SUFFIX` | Suffix to remove from filenames (default: " (1)") |
| `--extensions EXT1,EXT2,...` | Comma-separated list of file extensions to process (e.g., "mpg,avi,png") |
| `--overwrite` | Overwrite existing XMP sidecar files |

### Metadata Options

| Option | Description |
|--------|-------------|
| `--fix-metadata` | Fix metadata for problematic file types (MPG, AVI, PNG, AAE) |
| `--check-metadata` | Check which files in the new directory need metadata updates from the old directory |
| `--status-log FILE` | Log file for metadata status (default: metadata_status.log) |
| `--processed-log FILE` | Log file for processed files |
| `--failed-updates-log FILE` | Log file for failed metadata updates |

### Apple Photos Integration Options

| Option | Description |
|--------|-------------|
| `--import-to-photos` | Import photos to Apple Photos after fixing metadata |
| `--import-with-albums` | Import photos to Apple Photos and organize them into albums based on Google Takeout structure |

## 📋 Common Workflows

### 1. Basic Metadata Synchronization

```bash
python3 main.py
```

This will scan the `old` and `new` directories, match files, and apply metadata from Google Takeout JSON files to the corresponding files in the `new` directory.

### 2. Metadata Synchronization with Direct Import

```bash
python3 main.py --import-to-photos
```

This will fix metadata and then import the photos directly into Apple Photos.

### 3. Full Migration with Album Organization

```bash
python3 main.py --copy-to-new --import-with-albums
```

This will copy files from the `old` directory to the `new` directory, fix metadata, and then import the photos into Apple Photos while preserving the album structure from Google Takeout.

### 4. Finding and Removing Duplicates

```bash
# Find duplicates
python3 main.py --find-duplicates-only

# Remove duplicates
python3 main.py --remove-duplicates
```

This will first find duplicates and then remove them based on the generated duplicates.log file.

### 5. Fixing Problematic File Types

```bash
python3 main.py --fix-metadata --extensions mpg,avi,png
```

This will apply specialized metadata handling for problematic file types like MPG, AVI, and PNG.

### 6. Standalone Photo Import

```bash
# Import all photos
python3 import_to_photos.py

# Import with album organization
python3 import_to_photos.py --with-albums

# Import a specific file
python3 import_to_photos.py --specific-file new/photo.jpg
```

This will import photos directly into Apple Photos without modifying metadata.

## 📊 Log Files

All log files are stored in the `logs` directory by default:

- `metadata_sync.log`: Main log file with general information
- `processed_files.log`: Log of all processed files
- `failed_updates.log`: Log of files that failed metadata updates
- `duplicates.log`: Log of duplicate files
- `name_duplicates.log`: Log of files with duplicate names
- `metadata_status.log`: Log of metadata status for files
- `photos_import_progress.json`: Progress file for Apple Photos import

## 🔍 Troubleshooting

If you encounter issues:

1. Run with the `--verbose` flag to get more detailed logs
2. Check the `failed_updates.log` file for specific error messages
3. Try using `--fix-metadata` for problematic file types
4. For import issues, try using the standalone `import_to_photos.py` script with a specific file
