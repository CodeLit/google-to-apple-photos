#!/usr/bin/env python3
"""
Script to fix files that failed metadata updates
This script reads the failed_updates.log file and applies specialized metadata handling
"""
import os
import sys
import logging
import csv
import argparse
from datetime import datetime

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.exiftool_service import ExifToolService

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(),
		logging.FileHandler('fix_failed_updates.log')
	]
)
logger = logging.getLogger(__name__)

def main():
	"""Main function to fix failed metadata updates"""
	parser = argparse.ArgumentParser(description='Fix files that failed metadata updates')
	parser.add_argument('--failed-log', default='failed_updates.log', help='Log file with failed updates (default: failed_updates.log)')
	parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without modifying any files')
	parser.add_argument('--limit', type=int, help='Limit processing to specified number of files')
	args = parser.parse_args()
	
	# Check if exiftool is installed
	if not ExifToolService.check_exiftool():
		return 1
	
	# Check if the failed updates log exists
	if not os.path.exists(args.failed_log):
		logger.error(f"Failed updates log not found: {args.failed_log}")
		return 1
	
	# Read the failed updates log
	failed_files = []
	try:
		with open(args.failed_log, 'r') as f:
			reader = csv.reader(f)
			# Skip header
			next(reader, None)
			# Get unique file paths
			file_paths = set()
			for row in reader:
				if row and len(row) >= 1:
					file_path = row[0]
					if os.path.exists(file_path):
						file_paths.add(file_path)
					else:
						logger.warning(f"File not found: {file_path}")
			
			failed_files = list(file_paths)
	except Exception as e:
		logger.error(f"Error reading failed updates log: {str(e)}")
		return 1
	
	logger.info(f"Found {len(failed_files)} unique files that failed metadata updates")
	
	# Limit processing if requested
	if args.limit and args.limit > 0 and args.limit < len(failed_files):
		logger.info(f"Limiting processing to {args.limit} files")
		failed_files = failed_files[:args.limit]
	
	# Create output log file for fixed files
	fixed_log_path = 'fixed_files.log'
	with open(fixed_log_path, 'w') as fixed_log:
		fixed_log.write("file_path,result,timestamp\n")
	
	# Process files
	success_count = 0
	failure_count = 0
	
	for i, file_path in enumerate(failed_files, 1):
		try:
			# Log progress
			if i % 10 == 0 or i == len(failed_files):
				logger.info(f"Progress: {i}/{len(failed_files)} files processed")
			
			# Get file extension
			file_ext = os.path.splitext(file_path)[1].lower()
			
			logger.info(f"Attempting to fix metadata for {file_path}")
			
			if args.dry_run:
				logger.info(f"[DRY RUN] Would fix metadata for {file_path}")
				result = "dry_run"
			else:
				# Apply specialized metadata handling
				if ExifToolService.apply_specialized_metadata_for_problematic_files(file_path):
					logger.info(f"Successfully fixed metadata for {file_path}")
					success_count += 1
					result = "success"
				else:
					logger.error(f"Failed to fix metadata for {file_path}")
					failure_count += 1
					result = "failure"
			
			# Log the result
			with open(fixed_log_path, 'a') as fixed_log:
				timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
				fixed_log.write(f"{file_path},{result},{timestamp}\n")
				
		except KeyboardInterrupt:
			logger.warning("Process interrupted by user")
			break
		except Exception as e:
			logger.error(f"Error processing {file_path}: {str(e)}")
			failure_count += 1
			
			# Log the error
			with open(fixed_log_path, 'a') as fixed_log:
				timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
				fixed_log.write(f"{file_path},error: {str(e)},{timestamp}\n")
	
	# Print summary
	logger.info("=" * 50)
	logger.info("Fix Failed Updates Summary:")
	logger.info(f"Total files processed: {len(failed_files)}")
	logger.info(f"Successfully fixed: {success_count} files")
	logger.info(f"Failed to fix: {failure_count} files")
	logger.info(f"Results written to: {fixed_log_path}")
	logger.info("=" * 50)
	
	if success_count > 0:
		logger.info("✅ Metadata fix completed!")
	else:
		logger.warning("⚠️ No files were successfully fixed.")
	
	return 0

if __name__ == '__main__':
	sys.exit(main())
