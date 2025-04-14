#!/usr/bin/env python3
"""
Main module for Google to Apple Photos Metadata Synchronizer
"""
import os
import sys
import logging
import argparse
from pathlib import Path

from src.services.exiftool_service import ExifToolService
from src.services.metadata_service import MetadataService


# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(),
		logging.FileHandler('metadata_sync.log')
	]
)
logger = logging.getLogger(__name__)


def main():
	"""Main function to run the metadata synchronization process"""
	parser = argparse.ArgumentParser(description='Synchronize metadata from Google Takeout to Apple Photos exports')
	parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without modifying any files')
	parser.add_argument('--old-dir', default='old', help='Directory with Google Takeout files (default: old)')
	parser.add_argument('--new-dir', default='new', help='Directory with Apple Photos exports (default: new)')
	args = parser.parse_args()
	
	logger.info("Starting metadata synchronization process")
	
	# Get absolute paths
	script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	old_dir = os.path.join(script_dir, args.old_dir)
	new_dir = os.path.join(script_dir, args.new_dir)
	
	# Check if required directories exist
	for directory, name in [(old_dir, 'old'), (new_dir, 'new')]:
		if not os.path.exists(directory):
			logger.error(f"Required directory '{name}' not found at {directory}")
			logger.info(f"Please create the directory and add the appropriate files")
			return 1
	
	# Check if exiftool is installed
	if not ExifToolService.check_exiftool():
		return 1
	
	if args.dry_run:
		logger.info("Performing dry run (no files will be modified)")
	
	# Find metadata pairs
	logger.info(f"Scanning directories: {old_dir} -> {new_dir}")
	metadata_pairs = MetadataService.find_metadata_pairs(old_dir, new_dir)
	logger.info(f"Found {len(metadata_pairs)} matching file pairs")
	
	# Process files
	success_count = 0
	failure_count = 0
	
	for json_file, new_file, metadata in metadata_pairs:
		try:
			# Get exiftool arguments
			exif_args = metadata.to_exiftool_args()
			
			# Apply metadata
			if ExifToolService.apply_metadata(new_file, exif_args, args.dry_run):
				success_count += 1
			else:
				failure_count += 1
				
		except Exception as e:
			logger.error(f"Error processing {json_file}: {str(e)}")
			failure_count += 1
	
	# Print summary
	logger.info("=" * 50)
	logger.info("Metadata Synchronization Summary:")
	logger.info(f"Successfully updated: {success_count} files")
	logger.info(f"Failed to update: {failure_count} files")
	logger.info(f"Not found: {len(metadata_pairs) - success_count - failure_count} files")
	logger.info("=" * 50)
	
	if success_count > 0:
		logger.info("✅ Metadata synchronization completed successfully!")
		logger.info("You can now import the files from the 'new' directory into Apple Photos.")
	else:
		logger.warning("⚠️ No files were successfully updated.")
	
	return 0


if __name__ == '__main__':
	sys.exit(main())
