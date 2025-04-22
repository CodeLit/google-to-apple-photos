# 📸 Universal Photo Manager

A comprehensive toolkit for managing, organizing, and preserving your photo and video collections across different platforms and services.

## 🎯 Purpose

Universal Photo Manager helps you maintain control over your personal media library by:

- Finding and eliminating duplicate photos and videos
- Preserving and synchronizing metadata (dates, locations, titles, etc.) between services
- Fixing incorrect file types and extensions
- Facilitating cross-platform migrations between photo services

Particularly useful when transferring between major photo platforms like Google Photos and Apple Photos, but works with any photo collection.

## ✨ Features

- **Duplicate Detection & Removal**: Find and eliminate redundant files using advanced image matching
- **Metadata Synchronization**: Apply accurate metadata from JSON sources (like Google Takeout) to media files
- **Smart File Matching**: Match files by name, hash, or visual similarity
- **File Extension Correction**: Automatically detect and fix incorrect file extensions
- **Format Conversion**: Convert between image formats when needed
- **Cross-Platform Migration**: Tools for smoother transitions between photo services
- **Parallel Processing**: Optimize performance with multi-threaded operations
- **Detailed Logging**: Track all operations with comprehensive logs
- **Apple Photos Integration**: Import directly to Apple Photos with album organization
- **Google Photos Support**: Work with Google Takeout exports to preserve metadata

## 🪜 Common Workflows

### Remove Duplicates Only

```bash
# Find and report duplicates
python main.py --find-duplicates-only

# Remove duplicates based on the report
python main.py --remove-duplicates
```

### Fix Metadata from Google Takeout

```bash
# Synchronize metadata from Google Takeout JSON files
python main.py --sync-metadata --source-dir google_takeout --target-dir my_photos
```

### Complete Google to Apple Migration

```bash
# Run the complete migration workflow
python main.py --google-to-apple --source-dir google_takeout --target-dir apple_import
```

### Universal Photo Management

```bash
# Run comprehensive organization on your photo library
python main.py --organize --fix-metadata --remove-duplicates --photo-dir my_photos
```

## 🛠️ Command Line Options

```
usage: main.py [-h] [--dry-run] [--source-dir SOURCE_DIR] [--target-dir TARGET_DIR]
               [--photo-dir PHOTO_DIR] [--limit LIMIT] [--verbose] [--quiet]
               [--find-duplicates-only] [--remove-duplicates]
               [--sync-metadata] [--google-to-apple] [--organize]
               [--fix-metadata] [--similarity SIMILARITY]

Universal Photo Manager - Organize, deduplicate, and synchronize your photo collection

options:
  -h, --help            show this help message and exit
  --dry-run             Perform a dry run without modifying any files
  --source-dir SOURCE_DIR
                        Source directory with original files (default: source)
  --target-dir TARGET_DIR
                        Target directory for processed files (default: target)
  --photo-dir PHOTO_DIR
                        Main photo directory for universal operations (default: photos)
  --limit LIMIT         Limit processing to specified number of files
  --verbose, -v         Enable verbose output
  --quiet, -q           Suppress warning messages
  --find-duplicates-only
                        Only find and report duplicates
  --remove-duplicates   Remove duplicate files based on analysis
  --sync-metadata       Synchronize metadata from source files to target files
  --google-to-apple     Run Google Photos to Apple Photos migration workflow
  --organize            Organize photos by date/location/etc.
  --fix-metadata        Fix and standardize metadata across collection
  --similarity SIMILARITY
                        Similarity threshold for image matching (0.0-1.0, default: 0.98)
  --import-to-photos    Import processed files to Apple Photos
  --import-with-albums  Import to Apple Photos with album organization
```

## 📦 Installation

1. Clone this repository

```bash
git clone https://github.com/yourusername/universal-photo-manager.git
cd universal-photo-manager
```

2. Install Python dependencies

```bash
pip install -r requirements.txt
```

3. Install external dependencies:
   - **exiftool** (required for metadata operations)
     - macOS: `brew install exiftool`
     - Linux: `apt-get install exiftool` or equivalent
     - Windows: Download from [exiftool.org](https://exiftool.org)

## 📋 Requirements

- Python 3.6 or higher
- exiftool (external dependency)
- Optional: Pillow and imagehash for improved image matching

## 🔍 How It Works

### Duplicate Detection

The tool uses several methods to identify duplicates:

1. **File hash comparison**: For exact binary matches
2. **Image hash comparison**: Finds visually identical images even with different compression
3. **Metadata analysis**: Compares dates, GPS data, and other metadata
4. **Filename analysis**: Identifies naming patterns that suggest duplicates

### Metadata Synchronization

When synchronizing metadata:

1. Files are matched between source and target directories
2. JSON metadata files (like those from Google Takeout) are parsed
3. Extracted metadata is applied to target files using exiftool
4. A detailed log of changes is maintained

### Google to Apple Migration

The specialized Google to Apple workflow:

1. Processes Google Takeout export with JSON metadata
2. Fixes file extensions and formats for Apple Photos compatibility
3. Applies correct metadata to all files
4. Optionally imports directly to Apple Photos
5. Preserves album structure when importing

## 📊 Usage Examples

### Basic Universal Organization

Clean up and organize your entire photo collection:

```bash
# Organize a photo directory with all features enabled
python main.py --photo-dir my_photos --organize --fix-metadata --remove-duplicates
```

### Google Photos to Apple Photos Migration

Complete migration workflow:

```bash
# Step 1: Prepare directories
mkdir -p google_takeout apple_photos

# Step 2: Extract Google Takeout archive to google_takeout directory

# Step 3: Run migration
python main.py --google-to-apple --source-dir google_takeout --target-dir apple_photos

# Step 4: Import to Apple Photos with albums
python main.py --target-dir apple_photos --import-with-albums
```

### Simple Duplicate Removal

Just find and remove duplicates:

```bash
# Find duplicates in a directory
python main.py --photo-dir my_photos --find-duplicates-only

# Review duplicates.log file, then remove duplicates
python main.py --photo-dir my_photos --remove-duplicates
```

## 🔧 Advanced Usage

### Working with Multiple Sources

```bash
# First process Google Takeout data
python main.py --sync-metadata --source-dir google_takeout --target-dir main_library

# Then process another source
python main.py --sync-metadata --source-dir iphone_backup --target-dir main_library

# Finally clean up the combined library
python main.py --photo-dir main_library --organize --remove-duplicates
```

## 🤝 Contributing

Contributions are welcome! If you'd like to improve this tool, please feel free to submit a pull request or open an issue on GitHub.

## 📝 License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the LICENSE file for details.
