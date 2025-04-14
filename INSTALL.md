# Installation Guide

## Prerequisites

1. **Python 3.6 or higher**
   - Check your Python version with `python --version` or `python3 --version`
   - Download from [python.org](https://www.python.org/downloads/) if needed

2. **ExifTool**
   - Required for reading and writing metadata to media files
   - Install on macOS:
     ```bash
     brew install exiftool
     ```
   - Install on Linux:
     ```bash
     sudo apt-get install libimage-exiftool-perl
     ```
   - Install on Windows:
     - Download from [exiftool.org](https://exiftool.org/)
     - Add to your PATH

## Setup

1. **Clone or download this repository**

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare your directories**
   - `./old` - Place Google Takeout export here (with JSON files)
   - `./new` - Place Apple Photos exports here
   - `./archive` - Optional backup location

## Verification

Verify that exiftool is properly installed:
```bash
exiftool -ver
```

You should see a version number if the installation was successful.
