# 📸 Main Goal: Synchronize Photo Metadata from Google Takeout to Apple Photos

## 🎯 Objective
Transfer accurate photo and video metadata (e.g. creation dates) from Google Takeout export to files for clean import into Apple Photos.

## 🪜 Steps Overview

1. **Export from Google Photos**  
   Export photos and videos using **Google Takeout** into the `./old` folder.  
   Ensure `.json` metadata files are included alongside media files.

2. **Export from Apple Photos**  
   Export all photos and videos from **Apple Photos Library** into the `./new` folder.  
   Use “Export Unmodified Originals” in Photos app for best results.

3. **Sync metadata**  
   Use `.json` files from `./old` to transfer creation dates and other metadata to corresponding files in `./new`.

4. **Apply metadata**  
   Apply metadata (e.g. `DateTimeOriginal`) to media files in `./new` using tools like `exiftool`.

5. **Re-import into Apple Photos**  
   Import updated files from `./new` back into **Apple Photos**.  
   Apple Photos will read and use the corrected metadata during import.
