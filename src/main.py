#!/usr/bin/env python3
"""
Main module for Google to Apple Photos Metadata Synchronizer
"""
import os
import sys
import logging
import argparse
import time
from pathlib import Path

import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.exiftool_service import ExifToolService
from services.metadata_service import MetadataService


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
	parser.add_argument('--limit', type=int, help='Limit processing to specified number of files')
	parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
	parser.add_argument('--quiet', '-q', action='store_true', help='Suppress warning messages about missing files')
	parser.add_argument('--no-hash-matching', action='store_true', help='Disable image hash matching (faster but less accurate)')
	parser.add_argument('--similarity', type=float, default=0.98, help='Similarity threshold for image matching (0.0-1.0, default: 0.98)')
	parser.add_argument('--find-duplicates-only', action='store_true', help='Only find and report duplicates without updating metadata')
	parser.add_argument('--processed-log', default='processed_files.log', help='Log file for processed files (default: processed_files.log)')
	parser.add_argument('--failed-updates-log', default='failed_updates.log', help='Log file for failed metadata updates (default: failed_updates.log)')
	parser.add_argument('--copy-to-new', action='store_true', help='Copy files from old directory to new directory before processing')
	parser.add_argument('--remove-duplicates', action='store_true', help='Remove duplicate files in the new directory based on duplicates.log')
	parser.add_argument('--duplicates-log', default='duplicates.log', help='Log file for duplicates (default: duplicates.log)')
	parser.add_argument('--rename-files', action='store_true', help='Rename files by removing "(1)" from filenames')
	parser.add_argument('--rename-suffix', default=' (1)', help='Suffix to remove from filenames (default: " (1)")')
	parser.add_argument('--find-duplicates-by-name', action='store_true', help='Find duplicates by checking for files with the same base name but with "(1)" suffix')
	parser.add_argument('--name-duplicates-log', default='name_duplicates.log', help='Log file for name-based duplicates (default: name_duplicates.log)')
	parser.add_argument('--check-metadata', action='store_true', help='Check which files in the new directory need metadata updates from the old directory')
	parser.add_argument('--status-log', default='metadata_status.log', help='Log file for metadata status (default: metadata_status.log)')
	args = parser.parse_args()
	
	# Set logging level based on verbosity
	if args.verbose:
		logging.getLogger().setLevel(logging.DEBUG)
		logger.debug("Verbose logging enabled")
	elif args.quiet:
		logging.getLogger().setLevel(logging.ERROR)
	
	logger.info("Starting metadata synchronization process")
	start_time = time.time()
	
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
	
	# Set up the processed files and failed updates loggers
	MetadataService.setup_processed_files_logger(args.processed_log, args.failed_updates_log)
	
	# Copy files from old to new if requested
	if args.copy_to_new:
		logger.info(f"Copying media files from {old_dir} to {new_dir}...")
		copied_count = 0
		skipped_count = 0
		
		# Walk through the old directory
		for root, _, files in os.walk(old_dir):
			for file in files:
				# Skip JSON metadata files
				if file.endswith('.json'):
					continue
				
				# Get source and destination paths
				source_path = os.path.join(root, file)
				
				# Create relative path from old_dir
				rel_path = os.path.relpath(source_path, old_dir)
				
				# Skip if the file is in a subdirectory that's not a media file
				from utils.image_utils import is_media_file
				if not is_media_file(source_path):
					continue
				
				# Create destination path
				dest_path = os.path.join(new_dir, os.path.basename(source_path))
				
				# Skip if the file already exists in the new directory
				if os.path.exists(dest_path):
					skipped_count += 1
					continue
				
				try:
					# Copy the file
					import shutil
					shutil.copy2(source_path, dest_path)
					copied_count += 1
					
					# Log progress every 100 files
					if copied_count % 100 == 0:
						logger.info(f"Copied {copied_count} files to {new_dir}")
				except Exception as e:
					logger.error(f"Error copying {source_path} to {dest_path}: {str(e)}")
		
		logger.info(f"Finished copying files. Copied {copied_count} files, skipped {skipped_count} existing files.")
	
	# Remove duplicates if requested
	if args.remove_duplicates:
		from utils.image_utils import remove_duplicates
		logger.info(f"Removing duplicates based on {args.duplicates_log}...")
		
		# Check if the duplicates log exists
		if not os.path.exists(args.duplicates_log):
			logger.error(f"Duplicates log file not found: {args.duplicates_log}")
			logger.info("Run the script with --find-duplicates-only first to generate the duplicates log")
			return 1
		
		# Remove duplicates
		processed, removed = remove_duplicates(args.duplicates_log, args.dry_run)
		
		# Print summary
		if args.dry_run:
			logger.info(f"[DRY RUN] Would remove {removed} of {processed} duplicate files")
		else:
			logger.info(f"Removed {removed} of {processed} duplicate files")
		
		return 0
	
	# Rename files if requested
	if args.rename_files:
		from utils.image_utils import rename_files_remove_suffix
		logger.info(f"Renaming files by removing '{args.rename_suffix}' from filenames in {new_dir}...")
		
		# Rename files
		processed, renamed = rename_files_remove_suffix(new_dir, args.rename_suffix, args.dry_run)
		
		# Print summary
		if args.dry_run:
			logger.info(f"[DRY RUN] Would rename {renamed} of {processed} files")
		else:
			logger.info(f"Renamed {renamed} of {processed} files")
		
		return 0
	
	# Check metadata status if requested
	if args.check_metadata:
		from utils.image_utils import check_metadata_status
		logger.info(f"Checking metadata status for files in {new_dir}...")
		
		# Check metadata status
		total, with_metadata, without_metadata = check_metadata_status(old_dir, new_dir, args.status_log)
		
		# Print summary
		logger.info(f"Total files in {new_dir}: {total}")
		logger.info(f"Files with metadata available: {with_metadata} ({with_metadata/total*100:.1f}%)")
		logger.info(f"Files without metadata: {without_metadata} ({without_metadata/total*100:.1f}%)")
		logger.info(f"Detailed status written to {args.status_log}")
		
		return 0
	
	# Find duplicates by name if requested
	if args.find_duplicates_by_name:
		from utils.image_utils import find_duplicates_by_name
		logger.info(f"Finding duplicates by name in {new_dir}...")
		
		# Find and optionally remove duplicates by name
		found, removed = find_duplicates_by_name(new_dir, args.rename_suffix, args.dry_run, args.name_duplicates_log)
		
		# Print summary
		if args.dry_run:
			logger.info(f"[DRY RUN] Would remove {found} duplicate files")
		else:
			logger.info(f"Removed {removed} of {found} duplicate files")
		
		return 0
	
	# Find duplicates only if requested
	if args.find_duplicates_only:
		from utils.image_utils import find_duplicates
		logger.info(f"Finding duplicates in {new_dir}...")
		duplicates = find_duplicates(new_dir, args.similarity)
		if duplicates:
			dup_count = sum(len(dups) for dups in duplicates.values())
			logger.info(f"Found {dup_count} duplicate files in {len(duplicates)} groups")
			logger.info(f"Results written to {args.duplicates_log}")
		else:
			logger.info("No duplicates found")
		return 0
	
	# Find metadata pairs
	logger.info(f"Scanning directories: {old_dir} -> {new_dir}")
	use_hash_matching = not args.no_hash_matching
	metadata_pairs = MetadataService.find_metadata_pairs(old_dir, new_dir, 
												use_hash_matching=use_hash_matching, 
												similarity_threshold=args.similarity,
												duplicates_log=args.duplicates_log)
	
	if args.limit and args.limit > 0 and args.limit < len(metadata_pairs):
		logger.info(f"Limiting processing to {args.limit} of {len(metadata_pairs)} pairs")
		metadata_pairs = metadata_pairs[:args.limit]
	else:
		logger.info(f"Found {len(metadata_pairs)} matching file pairs")
	
	logger.info(f"Detailed processing log written to {args.processed_log}")
	
	# Process files
	success_count = 0
	failure_count = 0
	total_pairs = len(metadata_pairs)
	
	for i, (json_file, new_file, metadata) in enumerate(metadata_pairs, 1):
		try:
			# Log progress
			if i % 10 == 0 or i == total_pairs:
				logger.info(f"Progress: {i}/{total_pairs} files processed")
			
			# Get exiftool arguments
			exif_args = metadata.to_exiftool_args()
			
			# Apply metadata
			if ExifToolService.apply_metadata(new_file, exif_args, args.dry_run):
				success_count += 1
			else:
				# Try specialized handling for problematic file types
				file_ext = os.path.splitext(new_file)[1].lower()
				# Check if this is a problematic file type (MPG, AVI, PNG, AAE)
				if file_ext.lower() in ['.mpg', '.mpeg', '.avi', '.png', '.aae']:
					logger.info(f"Attempting specialized metadata handling for {new_file}")
					if not args.dry_run and ExifToolService.apply_specialized_metadata_for_problematic_files(new_file):
						logger.info(f"Successfully applied specialized metadata to {new_file}")
						success_count += 1
					else:
						failure_count += 1
						# Log the failed update with a specific error message
						error_message = f"Failed to apply metadata even with specialized handling for {file_ext} file"
						MetadataService.log_failed_update(new_file, error_message)
				else:
					failure_count += 1
					# Log the failed update with a more specific error message
					error_message = "Failed to apply complete metadata - partial or no metadata was applied"
					MetadataService.log_failed_update(new_file, error_message)
				
		except KeyboardInterrupt:
			logger.warning("Process interrupted by user")
			break
		except Exception as e:
			error_message = str(e)
			logger.error(f"Error processing {json_file}: {error_message}")
			failure_count += 1
			# Log the failed update with the specific error message
			MetadataService.log_failed_update(new_file, error_message)
	
	# Calculate elapsed time
	elapsed_time = time.time() - start_time
	minutes, seconds = divmod(elapsed_time, 60)
	
	# Print summary
	logger.info("=" * 50)
	logger.info("Metadata Synchronization Summary:")
	logger.info(f"Time elapsed: {int(minutes)} minutes, {int(seconds)} seconds")
	logger.info(f"Successfully updated: {success_count} files")
	logger.info(f"Failed to update: {failure_count} files")
	if failure_count > 0:
		logger.info(f"Failed updates are logged in: {args.failed_updates_log}")
	logger.info(f"Not processed: {total_pairs - success_count - failure_count} files")
	logger.info(f"Detailed processing log: {args.processed_log}")
	logger.info(f"Duplicates report: duplicates.log")
	logger.info("=" * 50)
	
	if success_count > 0:
		logger.info("✅ Metadata synchronization completed successfully!")
		logger.info("You can now import the files from the 'new' directory into Apple Photos.")
	else:
		logger.warning("⚠️ No files were successfully updated.")
	
	return 0


if __name__ == '__main__':
	sys.exit(main())
