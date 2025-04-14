#!/usr/bin/env python3
"""
Google Photos to Apple Photos Metadata Synchronizer

This script synchronizes metadata (especially dates) from Google Takeout JSON files
to corresponding media files exported from Apple Photos, allowing for correct
metadata when reimporting into Apple Photos.
"""

import os
import json
import glob
import subprocess
import argparse
from datetime import datetime
import logging
import re
import sys
from pathlib import Path

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

# Paths
OLD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'old')
NEW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'new')
ARCHIVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'archive')

def check_exiftool():
	"""Check if exiftool is installed."""
	try:
		subprocess.run(['exiftool', '-ver'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
		return True
	except (subprocess.SubprocessError, FileNotFoundError):
		logger.error("exiftool is not installed. Please install it to continue.")
		logger.info("On macOS, you can install it with: brew install exiftool")
		return False

def parse_json_metadata(json_file):
	"""
	Parse Google Takeout JSON metadata file and extract relevant information.
	
	Args:
		json_file (str): Path to the JSON metadata file
		
	Returns:
		dict: Dictionary containing extracted metadata
	"""
	try:
		with open(json_file, 'r', encoding='utf-8') as f:
			data = json.load(f)
		
		metadata = {}
		
		# Extract photoTakenTime
		if 'photoTakenTime' in data:
			timestamp = int(data['photoTakenTime']['timestamp'])
			formatted_date = datetime.fromtimestamp(timestamp).strftime('%Y:%m:%d %H:%M:%S')
			metadata['DateTimeOriginal'] = formatted_date
			metadata['CreateDate'] = formatted_date
			metadata['ModifyDate'] = formatted_date
		
		# Extract title if available
		if 'title' in data:
			metadata['Title'] = data['title']
			
		# Extract description if available
		if 'description' in data:
			metadata['Description'] = data['description']
			
		# Extract location data if available
		if 'geoData' in data and 'latitude' in data['geoData'] and 'longitude' in data['geoData']:
			metadata['GPSLatitude'] = data['geoData']['latitude']
			metadata['GPSLongitude'] = data['geoData']['longitude']
			
		return metadata
	except Exception as e:
		logger.error(f"Error parsing JSON file {json_file}: {str(e)}")
		return None

def get_base_filename(file_path):
	"""
	Extract base filename without extension from a file path.
	Handles special cases in Google Takeout naming.
	
	Args:
		file_path (str): Path to the file
		
	Returns:
		str: Base filename without extension
	"""
	filename = os.path.basename(file_path)
	
	# Handle edited files (filename(1).jpg)
	edited_match = re.match(r'(.+)(\(\d+\))(\..+)', filename)
	if edited_match:
		return edited_match.group(1)
	
	# Regular case
	return os.path.splitext(filename)[0]

def find_matching_file(base_name, target_dir):
	"""
	Find a file in target_dir that matches the base_name.
	
	Args:
		base_name (str): Base filename to match
		target_dir (str): Directory to search in
		
	Returns:
		str or None: Path to the matching file or None if not found
	"""
	# First try exact match
	for ext in ['.jpg', '.jpeg', '.png', '.mp4', '.mov', '.heic', '.gif']:
		exact_match = os.path.join(target_dir, f"{base_name}{ext}")
		if os.path.exists(exact_match):
			return exact_match
	
	# Try case-insensitive match
	for file in os.listdir(target_dir):
		file_base = get_base_filename(file)
		if file_base.lower() == base_name.lower():
			return os.path.join(target_dir, file)
	
	return None

def apply_metadata(file_path, metadata):
	"""
	Apply metadata to a file using exiftool.
	
	Args:
		file_path (str): Path to the file
		metadata (dict): Metadata to apply
		
	Returns:
		bool: True if successful, False otherwise
	"""
	if not metadata:
		return False
	
	try:
		cmd = ['exiftool']
		
		# Add each metadata field to the command
		for key, value in metadata.items():
			cmd.extend([f'-{key}={value}'])
		
		# Overwrite original file
		cmd.extend(['-overwrite_original', file_path])
		
		result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
		
		if result.returncode == 0:
			logger.info(f"Successfully updated metadata for {os.path.basename(file_path)}")
			return True
		else:
			logger.error(f"Failed to update metadata for {os.path.basename(file_path)}: {result.stderr.decode()}")
			return False
	except Exception as e:
		logger.error(f"Error applying metadata to {file_path}: {str(e)}")
		return False

def process_files():
	"""
	Process all JSON files in the old directory and apply metadata to matching files in the new directory.
	
	Returns:
		tuple: (success_count, failure_count, not_found_count)
	"""
	success_count = 0
	failure_count = 0
	not_found_count = 0
	
	# Get all JSON files in the old directory
	json_files = glob.glob(os.path.join(OLD_DIR, '**', '*.json'), recursive=True)
	total_files = len(json_files)
	
	logger.info(f"Found {total_files} JSON metadata files to process")
	
	for i, json_file in enumerate(json_files, 1):
		try:
			# Extract base name from JSON file
			json_base_name = get_base_filename(json_file)
			
			# Parse JSON metadata
			metadata = parse_json_metadata(json_file)
			
			if not metadata:
				logger.warning(f"No usable metadata found in {json_file}")
				failure_count += 1
				continue
			
			# Find matching file in new directory
			matching_file = find_matching_file(json_base_name, NEW_DIR)
			
			if matching_file:
				# Apply metadata to matching file
				if apply_metadata(matching_file, metadata):
					success_count += 1
				else:
					failure_count += 1
			else:
				logger.warning(f"No matching file found for {json_base_name}")
				not_found_count += 1
			
			# Log progress
			if i % 100 == 0 or i == total_files:
				logger.info(f"Progress: {i}/{total_files} files processed")
				
		except Exception as e:
			logger.error(f"Error processing {json_file}: {str(e)}")
			failure_count += 1
	
	return success_count, failure_count, not_found_count

def main():
	"""Main function to run the metadata synchronization process."""
	parser = argparse.ArgumentParser(description='Synchronize metadata from Google Takeout to Apple Photos exports')
	parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without modifying any files')
	args = parser.parse_args()
	
	logger.info("Starting metadata synchronization process")
	
	# Check if required directories exist
	for directory, name in [(OLD_DIR, 'old'), (NEW_DIR, 'new'), (ARCHIVE_DIR, 'archive')]:
		if not os.path.exists(directory):
			logger.error(f"Required directory '{name}' not found at {directory}")
			logger.info(f"Please create the directory and add the appropriate files")
			return 1
	
	# Check if exiftool is installed
	if not check_exiftool():
		return 1
	
	if args.dry_run:
		logger.info("Performing dry run (no files will be modified)")
	
	# Process files
	success_count, failure_count, not_found_count = process_files()
	
	# Print summary
	logger.info("=" * 50)
	logger.info("Metadata Synchronization Summary:")
	logger.info(f"Successfully updated: {success_count} files")
	logger.info(f"Failed to update: {failure_count} files")
	logger.info(f"Files not found: {not_found_count} files")
	logger.info("=" * 50)
	
	if success_count > 0:
		logger.info("✅ Metadata synchronization completed successfully!")
		logger.info("You can now import the files from the 'new' directory into Apple Photos.")
	else:
		logger.warning("⚠️ No files were successfully updated.")
	
	return 0

if __name__ == '__main__':
	sys.exit(main())
