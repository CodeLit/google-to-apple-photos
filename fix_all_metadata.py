#!/usr/bin/env python3
"""
Script to fix metadata for all file types in one go
"""
import os
import sys
import logging
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(),
		logging.FileHandler('fix_all_metadata.log')
	]
)
logger = logging.getLogger(__name__)

def find_json_metadata(file_path, old_dir):
	"""
	Find the corresponding JSON metadata file for a given file
	"""
	base_name = os.path.basename(file_path)
	name_without_ext = os.path.splitext(base_name)[0]
	
	# For AAE files, extract the base image name they're associated with
	if file_path.lower().endswith('.aae'):
		# AAE files often have names like IMG_1234O.aae or IMG_O1234.aae
		# Try to extract the base number
		import re
		base_match = re.search(r'IMG_[O]?([0-9]+)', name_without_ext)
		if base_match:
			base_number = base_match.group(1)
			# Try both IMG_1234.json and IMG_1234(1).json
			possible_json_names = [
				f"IMG_{base_number}.json",
				f"IMG_{base_number}(1).json"
			]
			
			for json_name in possible_json_names:
				json_path = os.path.join(old_dir, json_name)
				if os.path.exists(json_path):
					try:
						with open(json_path, 'r') as f:
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
							logger.info(f"Found metadata for {file_path} in {json_path}")
							return date_taken
					except Exception as e:
						logger.warning(f"Error reading JSON file {json_path}: {str(e)}")
	
	# For PNG files, try to extract date from filename if it contains a date pattern
	if file_path.lower().endswith('.png'):
		# Look for date patterns in the filename
		import re
		
		# Try to find YYYY-MM-DD pattern
		date_match = re.search(r'(20\d{2})[-_](\d{1,2})[-_](\d{1,2})', name_without_ext)
		if date_match:
			year, month, day = date_match.groups()
			try:
				date_taken = datetime(int(year), int(month), int(day), 12, 0, 0)  # Default to noon
				logger.info(f"Extracted date {date_taken} from filename {base_name}")
				return date_taken
			except ValueError:
				pass
		
		# Try to find timestamp pattern (e.g., 1661585066767)
		timestamp_match = re.match(r'^(\d{10,13})$', name_without_ext)
		if timestamp_match:
			timestamp = int(timestamp_match.group(1))
			# Handle both seconds and milliseconds timestamps
			if len(timestamp_match.group(1)) > 10:  # Milliseconds
				timestamp = timestamp / 1000
			try:
				date_taken = datetime.fromtimestamp(timestamp)
				logger.info(f"Extracted date {date_taken} from timestamp filename {base_name}")
				return date_taken
			except ValueError:
				pass
	
	# Try direct filename matching as a fallback
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
					logger.info(f"Found metadata for {file_path} in {json_path}")
					return date_taken
			except Exception as e:
				logger.warning(f"Error reading JSON file {json_path}: {str(e)}")
	
	# If no metadata found, use file system timestamps as last resort
	try:
		creation_time = os.path.getctime(file_path)
		date_taken = datetime.fromtimestamp(creation_time)
		logger.info(f"Using file system creation time for {file_path}: {date_taken}")
		return date_taken
	except Exception as e:
		logger.warning(f"Could not get file creation time for {file_path}: {str(e)}")
	
	return None

def create_xmp_sidecar(file_path, date_taken, dry_run=False):
	"""
	Create an XMP sidecar file for files that can't have metadata embedded directly
	"""
	if dry_run:
		logger.info(f"[DRY RUN] Would create XMP sidecar for {file_path}")
		return True
	
	sidecar_path = f"{file_path}.xmp"
	date_str = date_taken.strftime('%Y:%m:%d %H:%M:%S')
	
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
		result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
		if result.returncode == 0:
			logger.info(f"Successfully created XMP sidecar for {file_path}")
			logger.info(f"Created XMP sidecar: {sidecar_path}")
			return True
		else:
			logger.error(f"Failed to create XMP sidecar for {file_path}: {result.stderr}")
			return False
	except Exception as e:
		logger.error(f"Error creating XMP sidecar for {file_path}: {str(e)}")
		return False

def update_file_metadata(file_path, date_taken, dry_run=False):
	"""
	Update metadata directly in the file if possible
	"""
	if dry_run:
		logger.info(f"[DRY RUN] Would update metadata for {file_path}")
		return True
	
	date_str = date_taken.strftime('%Y:%m:%d %H:%M:%S')
	
	cmd = [
		'exiftool',
		f'-DateTimeOriginal={date_str}',
		f'-CreateDate={date_str}',
		f'-ModifyDate={date_str}',
		'-overwrite_original',
		file_path
	]
	
	try:
		result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
		if result.returncode == 0:
			logger.info(f"Successfully updated metadata for {file_path}")
			return True
		else:
			logger.error(f"Failed to update metadata for {file_path}: {result.stderr}")
			return False
	except Exception as e:
		logger.error(f"Error updating metadata for {file_path}: {str(e)}")
		return False

def process_file(file_path, old_dir, dry_run=False):
	"""
	Process a single file
	"""
	logger.info(f"Processing {file_path}")
	
	# Find corresponding JSON metadata
	date_taken = find_json_metadata(file_path, old_dir)
	if not date_taken:
		logger.warning(f"No metadata found for {file_path}")
		return False
	
	# Get file extension
	file_ext = os.path.splitext(file_path)[1].lower()
	
	# For video files and other problematic formats, create XMP sidecar
	if file_ext in ['.mpg', '.avi', '.png', '.aae']:
		return create_xmp_sidecar(file_path, date_taken, dry_run)
	else:
		# For other file types, try direct update first
		success = update_file_metadata(file_path, date_taken, dry_run)
		if not success:
			# If direct update fails, try sidecar as fallback
			logger.info(f"Direct update failed for {file_path}, trying sidecar approach")
			return create_xmp_sidecar(file_path, date_taken, dry_run)
		return success

def main():
	parser = argparse.ArgumentParser(description='Fix metadata for all file types')
	parser.add_argument('--old-dir', type=str, default='./old', help='Directory containing original files with JSON metadata')
	parser.add_argument('--new-dir', type=str, default='./new', help='Directory containing files to update')
	parser.add_argument('--extensions', type=str, help='Comma-separated list of file extensions to process (e.g., "mpg,avi,png")')
	parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without making changes')
	args = parser.parse_args()
	
	# Validate directories
	if not os.path.isdir(args.old_dir):
		logger.error(f"Old directory not found: {args.old_dir}")
		return 1
	
	if not os.path.isdir(args.new_dir):
		logger.error(f"New directory not found: {args.new_dir}")
		return 1
	
	# Find files to process
	files_to_process = []
	
	if args.extensions:
		# Process specific file extensions
		extensions = [f".{ext.lower().strip()}" for ext in args.extensions.split(',')]
		for ext in extensions:
			for file_path in Path(args.new_dir).glob(f"*{ext}"):
				files_to_process.append(str(file_path))
		logger.info(f"Found {len(files_to_process)} files with extensions {args.extensions}")
	else:
		# Process all files
		for file_path in Path(args.new_dir).glob("*.*"):
			file_path_str = str(file_path)
			# Skip XMP sidecar files and hidden files
			if not file_path_str.endswith('.xmp') and not os.path.basename(file_path_str).startswith('.'):
				files_to_process.append(file_path_str)
		logger.info(f"Found {len(files_to_process)} files to process")
	
	if args.dry_run:
		logger.info("Performing dry run, no changes will be made")
	
	# Process files
	success_count = 0
	failure_count = 0
	
	for i, file_path in enumerate(files_to_process):
		if (i + 1) % 10 == 0 or i + 1 == len(files_to_process):
			logger.info(f"Progress: {i+1}/{len(files_to_process)} files processed")
		
		if process_file(file_path, args.old_dir, args.dry_run):
			success_count += 1
		else:
			failure_count += 1
	
	# Summary
	logger.info("==================================================")
	logger.info("Metadata Fix Summary:")
	logger.info(f"Total files processed: {len(files_to_process)}")
	logger.info(f"Successfully processed: {success_count} files")
	logger.info(f"Failed to process: {failure_count} files")
	logger.info("Results written to: fix_all_metadata.log")
	logger.info("==================================================")
	
	if success_count > 0:
		logger.info("✅ Metadata fix completed!")
		logger.info("Some files have XMP sidecar files created alongside them.")
		logger.info("These will be recognized by Apple Photos when importing.")
	else:
		logger.info("❌ No files were successfully processed.")
	
	return 0

if __name__ == '__main__':
	sys.exit(main())
