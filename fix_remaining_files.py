#!/usr/bin/env python3
"""
Script to handle any remaining files that failed metadata updates
"""
import os
import sys
import logging
import argparse
import subprocess
import csv
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(),
		logging.FileHandler('fix_remaining_files.log')
	]
)
logger = logging.getLogger(__name__)

def find_json_metadata(file_path, old_dir):
	"""
	Find the corresponding JSON metadata file for a given file
	"""
	base_name = os.path.basename(file_path)
	name_without_ext = os.path.splitext(base_name)[0]
	
	# Try different variations of the filename
	possible_json_names = [
		f"{name_without_ext}.json",
		f"{name_without_ext}(1).json",
		f"{name_without_ext.replace('(1)', '')}.json"
	]
	
	for json_name in possible_json_names:
		json_path = os.path.join(old_dir, json_name)
		if os.path.exists(json_path):
			try:
				with open(json_path, 'r') as f:
					import json
					data = json.load(f)
					
				# Extract date taken
				date_taken = None
				if 'photoTakenTime' in data and 'timestamp' in data['photoTakenTime']:
					timestamp = int(data['photoTakenTime']['timestamp'])
					date_taken = datetime.fromtimestamp(timestamp)
				elif 'creationTime' in data and 'timestamp' in data['creationTime']:
					timestamp = int(data['creationTime']['timestamp'])
					date_taken = datetime.fromtimestamp(timestamp)
				
				if date_taken:
					return {
						'date_taken': date_taken,
						'json_path': json_path
					}
			except Exception as e:
				logger.warning(f"Error reading JSON file {json_path}: {str(e)}")
	
	return None

def process_file(file_path, old_dir, dry_run=False):
	"""
	Process a single file that failed metadata updates
	"""
	logger.info(f"Processing file: {file_path}")
	
	file_ext = os.path.splitext(file_path)[1].lower()
	
	# Find metadata from JSON
	metadata = find_json_metadata(file_path, old_dir)
	if not metadata:
		logger.warning(f"No metadata found for {file_path}")
		return False
	
	date_taken = metadata['date_taken']
	date_str = date_taken.strftime('%Y:%m:%d %H:%M:%S')
	
	success = False
	
	if file_ext in ['.png', '.aae']:
		# For PNG and AAE files, create a sidecar file
		sidecar_path = f"{file_path}.xmp"
		
		if dry_run:
			logger.info(f"[DRY RUN] Would create XMP sidecar for {file_path}")
			return True
		
		# Use exiftool to create the XMP sidecar
		cmd = [
			'exiftool',
			'-o', sidecar_path,
			f'-DateTimeOriginal={date_str}',
			f'-CreateDate={date_str}',
			f'-ModifyDate={date_str}',
			'-xmp:all',
			file_path
		]
		
		try:
			result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
			if result.returncode == 0:
				logger.info(f"Successfully created XMP sidecar for {file_path}")
				success = True
			else:
				logger.warning(f"Failed to create XMP sidecar: {result.stderr}")
		except Exception as e:
			logger.error(f"Error creating XMP sidecar: {str(e)}")
	else:
		# For other file types, try direct metadata update
		if dry_run:
			logger.info(f"[DRY RUN] Would update metadata for {file_path}")
			return True
		
		cmd = [
			'exiftool',
			f'-DateTimeOriginal={date_str}',
			f'-CreateDate={date_str}',
			f'-ModifyDate={date_str}',
			'-overwrite_original',
			file_path
		]
		
		try:
			result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
			if result.returncode == 0:
				logger.info(f"Successfully updated metadata for {file_path}")
				success = True
			else:
				logger.warning(f"Failed to update metadata: {result.stderr}")
		except Exception as e:
			logger.error(f"Error updating metadata: {str(e)}")
	
	return success

def main():
	parser = argparse.ArgumentParser(description='Fix remaining files that failed metadata updates')
	parser.add_argument('--old-dir', type=str, default='./old', help='Directory containing original files with JSON metadata')
	parser.add_argument('--new-dir', type=str, default='./new', help='Directory containing files to update')
	parser.add_argument('--failed-log', type=str, default='./failed_updates.log', help='Path to the failed updates log file')
	parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making changes')
	args = parser.parse_args()
	
	# Validate directories
	if not os.path.isdir(args.old_dir):
		logger.error(f"Old directory not found: {args.old_dir}")
		return 1
	
	if not os.path.isdir(args.new_dir):
		logger.error(f"New directory not found: {args.new_dir}")
		return 1
	
	# Process all PNG and AAE files in the new directory
	special_files = []
	for ext in ['.png', '.aae']:
		for file_path in Path(args.new_dir).glob(f'*{ext}'):
			special_files.append(str(file_path))
	
	logger.info(f"Found {len(special_files)} PNG/AAE files to process")
	
	# Process special files
	success_count = 0
	failure_count = 0
	
	for file_path in special_files:
		if process_file(file_path, args.old_dir, args.dry_run):
			success_count += 1
		else:
			failure_count += 1
	
	# Summary
	logger.info("==================================================")
	logger.info("Remaining Files Fix Summary:")
	logger.info(f"Total special files processed: {len(special_files)}")
	logger.info(f"Successfully processed: {success_count} files")
	logger.info(f"Failed to process: {failure_count} files")
	logger.info("==================================================")
	logger.info("✅ Remaining files fix completed!")
	
	return 0

if __name__ == '__main__':
	sys.exit(main())
