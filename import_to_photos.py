#!/usr/bin/env python3
"""
Script to import photos directly to Apple Photos
"""
import os
import sys
import logging
import argparse
from pathlib import Path

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.photos_app_service import PhotosAppService

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler()
	]
)
logger = logging.getLogger(__name__)

def main():
	"""Main function to run the photo import process"""
	parser = argparse.ArgumentParser(description='Import photos from Google Takeout to Apple Photos')
	parser.add_argument('--takeout-dir', default='old', help='Directory with Google Takeout files (default: old)')
	parser.add_argument('--with-albums', action='store_true', help='Organize photos into albums based on Google Takeout structure')
	parser.add_argument('--specific-file', help='Import a specific file instead of a directory')
	args = parser.parse_args()
	
	# Get absolute paths
	script_dir = os.path.dirname(os.path.abspath(__file__))
	takeout_dir = os.path.join(script_dir, args.takeout_dir)
	
	# Check if required directories exist
	if not os.path.exists(takeout_dir):
		logger.error(f"Required directory not found at {takeout_dir}")
		logger.info(f"Please create the directory and add the appropriate files")
		return 1
	
	# Import a specific file if requested
	if args.specific_file:
		file_path = args.specific_file
		if not os.path.isabs(file_path):
			file_path = os.path.join(script_dir, file_path)
		
		if not os.path.exists(file_path):
			logger.error(f"File not found: {file_path}")
			return 1
		
		# Get timestamp from metadata if available
		timestamp = PhotosAppService.get_photo_timestamp(file_path)
		
		logger.info(f"Importing file: {file_path}")
		result = PhotosAppService.import_photo(file_path, timestamp)
		
		if result:
			logger.info(f"Photo already exists in library: {os.path.basename(file_path)}")
		else:
			logger.info(f"Successfully imported: {os.path.basename(file_path)}")
		
		return 0
	
	# Import all photos from the takeout directory
	logger.info(f"Importing photos from {takeout_dir} to Apple Photos...")
	
	if args.with_albums:
		logger.info("Organizing photos into albums based on Google Takeout structure...")
		imported, skipped = PhotosAppService.import_photos_from_directory(takeout_dir, with_albums=True)
	else:
		imported, skipped = PhotosAppService.import_photos_from_directory(takeout_dir, with_albums=False)
	
	logger.info(f"Import complete. Imported: {imported}, Already in library: {skipped}")
	return 0

if __name__ == '__main__':
	sys.exit(main())
