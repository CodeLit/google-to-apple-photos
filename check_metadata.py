#!/usr/bin/env python3
"""
Simple script to check metadata status
"""
import os
import logging
import sys
from typing import Tuple
import json

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(),
	]
)
logger = logging.getLogger(__name__)

def is_media_file(file_path: str) -> bool:
	"""Check if a file is a media file based on its extension"""
	media_extensions = [
		'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp',
		'.mp4', '.mov', '.avi', '.wmv', '.flv', '.mkv', '.webm', '.m4v',
		'.heic', '.heif'
	]
	_, ext = os.path.splitext(file_path.lower())
	return ext in media_extensions

def check_metadata_status(old_dir: str, new_dir: str, status_log: str = 'metadata_status.log') -> Tuple[int, int, int]:
	"""
	Check which files in the new directory need metadata updates from the old directory
	
	Args:
		old_dir: Directory with Google Takeout files
		new_dir: Directory with Apple Photos exports
		status_log: Path to the log file to write the results to
		
	Returns:
		Tuple of (total files in new, files with metadata in old, files without metadata in old)
	"""
	logger.info(f"Checking metadata status for files in {new_dir}...")
	
	# Get all media files in the new directory
	new_files = []
	for root, _, files in os.walk(new_dir):
		for filename in files:
			file_path = os.path.join(root, filename)
			if is_media_file(file_path):
				new_files.append(file_path)
	
	logger.info(f"Found {len(new_files)} media files in {new_dir}")
	
	# Pre-index all JSON files in the old directory
	logger.info(f"Indexing JSON files in {old_dir}...")
	json_files_map = {}
	json_count = 0
	
	for root, _, files in os.walk(old_dir):
		for filename in files:
			if filename.endswith('.json'):
				json_path = os.path.join(root, filename)
				json_count += 1
				
				# Store the JSON file path with the base filename as key
				# Remove the .supplemental-metadata.json suffix if present
				base_name = filename
				if '.supplemental-metadata.json' in filename:
					base_name = filename.replace('.supplemental-metadata.json', '')
				elif '.json' in filename:
					base_name = filename.replace('.json', '')
				
				# Add to map with both the full name and potential base name
				json_files_map[filename] = json_path
				json_files_map[base_name] = json_path
	
	logger.info(f"Indexed {json_count} JSON files from {old_dir}")
	
	# Find corresponding JSON files in the old directory
	files_with_metadata = []
	files_without_metadata = []
	
	# Process only a subset of files for testing
	test_limit = 100
	logger.info(f"Testing with first {test_limit} files for quicker results")
	
	for i, new_file in enumerate(new_files):
		if i >= test_limit:
			break
			
		new_filename = os.path.basename(new_file)
		json_found = False
		
		# Check if we have a matching JSON file
		potential_matches = [
			new_filename + '.supplemental-metadata.json',
			new_filename + '.json',
			new_filename
		]
		
		for match in potential_matches:
			if match in json_files_map:
				json_path = json_files_map[match]
				
				# Check if the JSON file contains photoTakenTime
				try:
					with open(json_path, 'r', encoding='utf-8') as f:
						metadata = json.load(f)
						if 'photoTakenTime' in metadata:
							files_with_metadata.append((new_file, json_path))
							json_found = True
							break
				except Exception as e:
					logger.error(f"Error reading JSON file {json_path}: {str(e)}")
					continue
		
		if not json_found:
			files_without_metadata.append(new_file)
	
	logger.info(f"Found metadata for {len(files_with_metadata)} files")
	logger.info(f"Missing metadata for {len(files_without_metadata)} files")
	
	# Write to log file
	with open(status_log, 'w', encoding='utf-8') as f:
		f.write("# Files with metadata available\n")
		f.write("new_file,json_file\n")
		for new_file, json_path in files_with_metadata:
			f.write(f"{new_file},{json_path}\n")
		
		f.write("\n# Files without metadata\n")
		for new_file in files_without_metadata:
			f.write(f"{new_file}\n")
	
	logger.info(f"Metadata status written to {status_log}")
	return len(new_files), len(files_with_metadata), len(files_without_metadata)

if __name__ == "__main__":
	script_dir = os.path.dirname(os.path.abspath(__file__))
	old_dir = os.path.join(script_dir, 'old')
	new_dir = os.path.join(script_dir, 'new')
	
	# Check if required directories exist
	for directory, name in [(old_dir, 'old'), (new_dir, 'new')]:
		if not os.path.exists(directory):
			logger.error(f"Required directory '{name}' not found at {directory}")
			logger.info(f"Please create the directory and add the appropriate files")
			sys.exit(1)
	
	# Run the metadata status check
	total, with_metadata, without_metadata = check_metadata_status(old_dir, new_dir)
	
	# Print summary
	logger.info(f"Total files in {new_dir}: {total}")
	logger.info(f"Files with metadata available: {with_metadata}")
	logger.info(f"Files without metadata: {without_metadata}")
