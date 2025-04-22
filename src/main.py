#!/usr/bin/env python3
"""
Main module for Google to Apple Photos Metadata Synchronizer
"""
import os
import sys
import json
import logging
import argparse
import time
import re
import subprocess
from pathlib import Path
from datetime import datetime

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.exiftool_service import ExifToolService
from src.services.metadata_service import MetadataService

from src.services.copy_service import CopyService
from src.utils.file_utils import extract_date_from_filename

# Configure logging
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_dir = os.path.join(project_root, "logs")
data_dir = os.path.join(project_root, "data")
os.makedirs(log_dir, exist_ok=True)
os.makedirs(data_dir, exist_ok=True)

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(),
		logging.FileHandler(os.path.join(log_dir, 'metadata_sync.log'))
	]
)
logger = logging.getLogger(__name__)


def find_json_metadata(file_path, old_dir):
	"""
	Find the corresponding JSON metadata file for a given file
	"""
	logger.debug(f"Looking for metadata for {os.path.basename(file_path)}")
	base_name = os.path.basename(file_path)
	name_without_ext = os.path.splitext(base_name)[0]
	
	# Special handling for AAE files
	if file_path.lower().endswith('.aae'):
		# AAE files often have names like IMG_1234O.aae or IMG_1234(1)O.aae
		# Try to find the corresponding JSON by removing the O suffix and any (1) parts
		match = re.match(r'(.+?)(?:\(\d+\))?O\.aae$', base_name, re.IGNORECASE)
		if match:
			base_name_without_o = match.group(1)
			possible_json_names = [
				f"{base_name_without_o}.json",
				f"{base_name_without_o}(1).json",
				f"{base_name_without_o.replace('IMG_', '')}.json"
			]
			
			# Recursively search for JSON files in old_dir and its subdirectories
			for root, _, files in os.walk(old_dir):
				for json_name in possible_json_names:
					if json_name in files:
						json_path = os.path.join(root, json_name)
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
								logger.info(f"Found metadata for AAE file {file_path} in {json_path}")
								return {
									'date_taken': date_taken,
									'json_path': json_path,
									'data': data
								}
						except Exception as e:
							logger.warning(f"Error reading JSON file {json_path}: {str(e)}")
	
	# Try to extract date from filename patterns using the utility function
	date_info = extract_date_from_filename(file_path)
	if date_info:
		date_str, pattern_desc = date_info
		try:
			# Parse the date string (format: YYYY:MM:DD)
			year, month, day = date_str.split(':')
			
			# Check if this is a pattern with time component
			if "YYYY-MM-DD_HH-MM-SS pattern" in pattern_desc:
				# Extract time from filename
				time_match = re.search(r'_([0-9]{2})-([0-9]{2})-([0-9]{2})', base_name)
				if time_match:
					hour = int(time_match.group(1))
					minute = int(time_match.group(2))
					second = int(time_match.group(3))
					date_taken = datetime(int(year), int(month), int(day), hour, minute, second)
				else:
					# Fallback to noon if time extraction fails
					date_taken = datetime(int(year), int(month), int(day), 12, 0, 0)
			else:
				# For patterns without time, set to noon
				date_taken = datetime(int(year), int(month), int(day), 12, 0, 0)
			
			logger.info(f"Extracted date {date_taken} from filename {base_name} using {pattern_desc}")
			return {
				'date_taken': date_taken,
				'json_path': None,
				'data': None
			}
		except ValueError as e:
			logger.warning(f"Error parsing date from filename {base_name}: {str(e)}")
			pass
			
	# Legacy pattern like image_2021-03-07_235256.png
	date_match = re.search(r'image_(\d{4}-\d{2}-\d{2})_', base_name)
	if date_match:
		date_str = date_match.group(1)
		try:
			date_taken = datetime.strptime(date_str, '%Y-%m-%d')
			date_taken = date_taken.replace(hour=12)  # Set to noon if no time
			logger.info(f"Extracted date {date_taken} from filename {base_name}")
			return {
				'date_taken': date_taken,
				'json_path': None,
				'data': None
			}
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
			return {
				'date_taken': date_taken,
				'json_path': None,
				'data': None
			}
		except ValueError:
			pass
	
	# Try direct filename matching as a fallback
	possible_json_names = [
		f"{name_without_ext}.json",
		f"{name_without_ext}(1).json",
		f"{name_without_ext.replace('(1)', '')}.json"
	]
	
	# Recursively search for JSON files in old_dir and its subdirectories
	for root, _, files in os.walk(old_dir):
		for json_name in possible_json_names:
			if json_name in files:
				json_path = os.path.join(root, json_name)
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
						return {
							'date_taken': date_taken,
							'json_path': json_path,
							'data': data
						}
				except Exception as e:
					logger.warning(f"Error reading JSON file {json_path}: {str(e)}")
	
	# If no metadata found, use file system timestamps as last resort
	try:
		creation_time = os.path.getctime(file_path)
		date_taken = datetime.fromtimestamp(creation_time)
		logger.info(f"Using file system creation time for {file_path}: {date_taken}")
		return {
			'date_taken': date_taken,
			'json_path': None,
			'data': None
		}
	except Exception as e:
		logger.warning(f"Could not get file creation time for {file_path}: {str(e)}")
	
	return None


def create_xmp_sidecar(file_path, metadata, dry_run=False, overwrite=False):
	"""
	Create an XMP sidecar file for files that can't have metadata embedded directly
	"""
	if dry_run:
		logger.info(f"[DRY RUN] Would create XMP sidecar for {file_path}")
		return True
	
	sidecar_path = f"{file_path}.xmp"
	
	# Check if sidecar already exists
	if os.path.exists(sidecar_path):
		if overwrite:
			logger.info(f"Overwriting existing XMP sidecar for {file_path}")
			try:
				os.remove(sidecar_path)
			except Exception as e:
				logger.error(f"Failed to remove existing XMP sidecar for {file_path}: {str(e)}")
				return False
		else:
			logger.info(f"XMP sidecar already exists for {file_path}, skipping")
			return True
	
	date_str = metadata['date_taken'].strftime('%Y:%m:%d %H:%M:%S')
	
	# Build exiftool command
	cmd = [
		'exiftool',
		'-o', sidecar_path,
		f'-DateTimeOriginal={date_str}',
		f'-CreateDate={date_str}',
		f'-ModifyDate={date_str}'
	]
	
	# Add GPS coordinates if available
	if metadata['data'] and 'geoData' in metadata['data']:
		geo_data = metadata['data']['geoData']
		if 'latitude' in geo_data and geo_data['latitude'] != 0:
			cmd.append(f'-GPSLatitude={geo_data["latitude"]}')
		if 'longitude' in geo_data and geo_data['longitude'] != 0:
			cmd.append(f'-GPSLongitude={geo_data["longitude"]}')
	
	# Add title/description if available
	if metadata['data']:
		if 'title' in metadata['data'] and metadata['data']['title']:
			cmd.append(f'-Title={metadata["data"]["title"]}')
		if 'description' in metadata['data'] and metadata['data']['description']:
			cmd.append(f'-Description={metadata["data"]["description"]}')
	
	# Add the file path
	cmd.append(file_path)
	
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


def update_file_metadata(file_path, metadata, dry_run=False):
	"""
	Update metadata directly in the file if possible
	"""
	if dry_run:
		logger.info(f"[DRY RUN] Would update metadata for {file_path}")
		return True
	
	date_str = metadata['date_taken'].strftime('%Y:%m:%d %H:%M:%S')
	
	# Build exiftool command
	cmd = [
		'exiftool',
		f'-DateTimeOriginal={date_str}',
		f'-CreateDate={date_str}',
		f'-ModifyDate={date_str}'
	]
	
	# Add GPS coordinates if available
	if metadata['data'] and 'geoData' in metadata['data']:
		geo_data = metadata['data']['geoData']
		if 'latitude' in geo_data and geo_data['latitude'] != 0:
			cmd.append(f'-GPSLatitude={geo_data["latitude"]}')
		if 'longitude' in geo_data and geo_data['longitude'] != 0:
			cmd.append(f'-GPSLongitude={geo_data["longitude"]}')
	
	# Add title/description if available
	if metadata['data']:
		if 'title' in metadata['data'] and metadata['data']['title']:
			cmd.append(f'-Title={metadata["data"]["title"]}')
		if 'description' in metadata['data'] and metadata['data']['description']:
			cmd.append(f'-Description={metadata["data"]["description"]}')
	
	# Add overwrite flag and file path
	cmd.extend(['-overwrite_original', file_path])
	
	try:
		result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
		if result.returncode == 0:
			logger.info(f"Successfully updated metadata for {file_path}")

			# Try to update filesystem creation date (macOS only)
			try:
				import platform
				if platform.system() == 'Darwin':
					# SetFile (macOS, needs Xcode Command Line Tools)
					creation_date = metadata['date_taken'].strftime('%m/%d/%Y %H:%M:%S')
					setfile_cmd = [
						'SetFile',
						'-d', creation_date,
						file_path
					]
					try:
						result_setfile = subprocess.run(setfile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
						if result_setfile.returncode != 0:
							logger.warning(f"SetFile failed for {file_path}: {result_setfile.stderr.strip()}")
					except Exception as e:
						logger.warning(f"SetFile exception for {file_path}: {str(e)}")
				# Always update mtime/atime
				mtime = atime = metadata['date_taken'].timestamp()
				os.utime(file_path, (atime, mtime))
			except Exception as e:
				logger.warning(f"Failed to update filesystem times for {file_path}: {str(e)}")

			return True
		else:
			logger.error(f"Failed to update metadata for {file_path}: {result.stderr}")
			return False
	except Exception as e:
		logger.error(f"Error updating metadata for {file_path}: {str(e)}")
		return False


def process_file(file_path, old_dir, dry_run=False, overwrite=False):
	"""
	Process a single file
	"""
	logger.info(f"Processing {os.path.basename(file_path)}")
	
	# Find corresponding JSON metadata or fallback to filename-based date
	metadata = find_json_metadata(file_path, old_dir)
	if not metadata:
		from src.utils.file_utils import extract_date_from_filename
		date_info = extract_date_from_filename(file_path)
		if date_info:
			date_str, pattern_desc = date_info
			from datetime import datetime
			# Try to extract time if possible
			filename = os.path.basename(file_path)
			time_match = None
			# photo_YYYY-MM-DD_HH-MM-SS
			photo_time = re.match(r'photo_([0-9]{4}-[0-9]{2}-[0-9]{2})_([0-9]{2}-[0-9]{2}-[0-9]{2})\..+', filename)
			if photo_time:
				dt = datetime.strptime(f"{photo_time.group(1)} {photo_time.group(2).replace('-', ':')}", '%Y-%m-%d %H:%M:%S')
			else:
				# YYYY-MM-DD_HH-MM-SS
				date_time = re.match(r'([0-9]{4}-[0-9]{2}-[0-9]{2})_([0-9]{2}-[0-9]{2}-[0-9]{2}).*\..+', filename)
				if date_time:
					dt = datetime.strptime(f"{date_time.group(1)} {date_time.group(2).replace('-', ':')}", '%Y-%m-%d %H:%M:%S')
				else:
					dt = datetime.strptime(date_str, '%Y:%m:%d')
			metadata = {'date_taken': dt, 'json_path': None, 'data': None}
		else:
			logger.warning(f"No metadata or valid date found for {file_path}")
			return False
	
	file_ext = os.path.splitext(file_path)[1].lower()
	if file_ext in ['.mpg', '.avi', '.png', '.aae']:
		return create_xmp_sidecar(file_path, metadata, dry_run, overwrite)
	else:
		success = update_file_metadata(file_path, metadata, dry_run)
		if not success:
			logger.info(f"Direct update failed for {file_path}, trying sidecar approach")
			return create_xmp_sidecar(file_path, metadata, dry_run, overwrite)
		return success


def fix_metadata(args):
	"""
	Fix metadata for all file types
	"""
	# Check if exiftool is installed
	if not ExifToolService.check_exiftool():
		logger.error("ExifTool is not installed or not in PATH. Please install ExifTool.")
		return 1
	
	# Get absolute paths for directories
	script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	old_dir = os.path.join(script_dir, args.old_dir) if not os.path.isabs(args.old_dir) else args.old_dir
	new_dir = os.path.join(script_dir, args.new_dir) if not os.path.isabs(args.new_dir) else args.new_dir
	
	# Debug output for paths
	logger.debug(f"Script directory: {script_dir}")
	logger.debug(f"Old directory absolute path: {old_dir}")
	logger.debug(f"New directory absolute path: {new_dir}")
	
	# Validate directories
	if not os.path.isdir(old_dir):
		logger.error(f"Old directory not found: {old_dir}")
		return 1
	
	if not os.path.isdir(new_dir):
		logger.error(f"New directory not found: {new_dir}")
		return 1
	
	# Find files to process
	files_to_process = []
	
	# Check if we have a metadata status file
	if args.status_log and os.path.isfile(args.status_log):
		try:
			import csv
			logger.info(f"Using metadata status file: {args.status_log}")
			with open(args.status_log, 'r') as f:
				reader = csv.reader(f)
				# Skip header
				header = next(reader, None)
				if header and len(header) >= 2:
					metadata_pairs = []
					for row in reader:
						if row and len(row) >= 2:
							new_file = row[0]
							json_file = row[1]
							if os.path.exists(new_file) and os.path.exists(json_file):
								files_to_process.append((new_file, json_file))
							else:
								if not os.path.exists(new_file):
									logger.warning(f"New file not found: {new_file}")
								if not os.path.exists(json_file):
									logger.warning(f"JSON file not found: {json_file}")
					logger.info(f"Found {len(files_to_process)} file pairs in metadata status file")
					if not files_to_process:
						logger.error("No valid file pairs found in metadata status file")
						return 1
					else:
						logger.info(f"Processing {len(files_to_process)} file pairs from metadata status file")
				else:
					logger.error(f"Invalid header in metadata status file: {header}")
					return 1
		except Exception as e:
			logger.error(f"Error reading metadata status file: {str(e)}")
			return 1
	elif args.failed_updates_log and os.path.isfile(args.failed_updates_log):
		# Process files from the failed log
		try:
			import csv
			logger.info(f"Using failed updates log: {args.failed_updates_log}")
			with open(args.failed_updates_log, 'r') as f:
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
				files_to_process = [(path, None) for path in file_paths]
			logger.info(f"Found {len(files_to_process)} files in failed updates log")
		except Exception as e:
			logger.error(f"Error reading failed updates log: {str(e)}")
			return 1
	elif args.extensions:
		# Process specific file extensions
		extensions = [ext.lower().strip() for ext in args.extensions.split(',')]
		logger.debug(f"Looking for files with extensions: {extensions}")
		for ext in extensions:
			# Search for both lowercase and uppercase extensions
			for pattern in [f"*.{ext}", f"*.{ext.upper()}"]:
				logger.debug(f"Searching with pattern: {pattern} in directory {new_dir}")
				count_before = len(files_to_process)
				for file_path in Path(new_dir).glob(pattern):
					files_to_process.append((str(file_path), None))
				count_after = len(files_to_process)
				logger.debug(f"Found {count_after - count_before} files with pattern {pattern}")
		logger.info(f"Found {len(files_to_process)} files with extensions {args.extensions}")
	else:
		# Process all files
		logger.info(f"Scanning for all files in {new_dir}")
		for file_path in Path(new_dir).glob("*.*"):
			file_path_str = str(file_path)
			# Skip XMP sidecar files and hidden files
			if not file_path_str.endswith('.xmp') and not os.path.basename(file_path_str).startswith('.'):
				files_to_process.append((file_path_str, None))
		logger.info(f"Found {len(files_to_process)} files to process")
	
	# Limit processing if requested
	if args.limit and args.limit > 0 and args.limit < len(files_to_process):
		logger.info(f"Limiting processing to {args.limit} files")
		files_to_process = files_to_process[:args.limit]
	
	if args.dry_run:
		logger.info("Performing dry run, no changes will be made")
	
	# Process files
	success_count = 0
	failure_count = 0
	
	# Create output log file for results
	results_log_path = os.path.join(data_dir, 'metadata_results.csv')
	logger.info(f"Results written to: {results_log_path}")
	with open(results_log_path, 'w') as results_log:
		results_log.write("file_path,result,timestamp\n")
	
	for i, file_info in enumerate(files_to_process):
		if isinstance(file_info, tuple) and len(file_info) == 2:
			file_path, json_path = file_info
		else:
			file_path = file_info
			json_path = None
		
		logger.info(f"Processing file {i+1}/{len(files_to_process)}: {os.path.basename(file_path)}")
		
		try:
			result = "failure"
			if json_path and os.path.exists(json_path):
				# If we have a specific JSON file, use it directly
				logger.debug(f"Using JSON file: {json_path} for {file_path}")
				metadata = MetadataService.extract_metadata_from_json(json_path)
				if metadata:
					# Convert Metadata object to exiftool arguments
					exiftool_args = []
					
					# Add date fields if available
					if metadata.date_taken:
						exiftool_args.extend([
							"-DateTimeOriginal=" + metadata.date_taken,
							"-CreateDate=" + metadata.date_taken,
							"-ModifyDate=" + metadata.date_taken
						])
					
					# Add GPS coordinates if available
					if metadata.latitude is not None and metadata.longitude is not None:
						exiftool_args.extend([
							"-GPSLatitude=" + str(metadata.latitude),
							"-GPSLongitude=" + str(metadata.longitude),
							"-GPSLatitudeRef=" + ("N" if metadata.latitude >= 0 else "S"),
							"-GPSLongitudeRef=" + ("E" if metadata.longitude >= 0 else "W")
						])
					
					# Add title if available
					if metadata.title:
						exiftool_args.append("-Title=" + metadata.title)
					
					if exiftool_args:
						logger.debug(f"Applying metadata with args: {exiftool_args}")
						if ExifToolService.apply_metadata(file_path, exiftool_args, args.dry_run):
							success_count += 1
							result = "success"
						else:
							failure_count += 1
					else:
						logger.warning(f"No metadata fields to apply for file: {file_path}")
						failure_count += 1
				else:
					logger.warning(f"No metadata found in JSON file: {json_path}")
					failure_count += 1
			else:
				# Otherwise, try to find matching JSON in old directory
				if process_file(file_path, old_dir, args.dry_run, args.overwrite):
					success_count += 1
					result = "success"
				else:
					failure_count += 1
			
			# Log the result
			with open(results_log_path, 'a') as results_log:
				timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
				results_log.write(f"{file_path},{result},{timestamp}\n")
		except KeyboardInterrupt:
			logger.warning("Process interrupted by user")
			break
		except Exception as e:
			logger.error(f"Error processing {file_path}: {str(e)}")
			failure_count += 1
			
			# Log the error
			with open(results_log_path, 'a') as results_log:
				timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
				results_log.write(f"{file_path},error: {str(e)},{timestamp}\n")
	
	# Summary
	logger.info("==================================================")
	logger.info("Metadata Fix Summary:")
	logger.info(f"Total files processed: {len(files_to_process)}")
	logger.info(f"Successfully processed: {success_count} files")
	logger.info(f"Failed to process: {failure_count} files")
	logger.info(f"Results written to: {results_log_path}")
	logger.info("==================================================")
	
	if success_count > 0:
		logger.info("✅ Metadata fix completed!")
		logger.info("Some files have XMP sidecar files created alongside them.")
		logger.info("These will be recognized by Apple Photos when importing.")
	else:
		logger.info("❌ No files were successfully processed.")
	


def main():
	"""Main function to run the metadata synchronization process
	
	By default, this function performs a complete workflow:
	1. Copy missing files from old directory to new directory
	2. Find and remove duplicates in the new directory
	3. Apply metadata from Google Takeout JSON files to files in the new directory
	"""
	parser = argparse.ArgumentParser(description='Synchronize metadata from Google Takeout to Apple Photos exports')
	parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without modifying any files')
	parser.add_argument('--old-dir', default='old', help='Directory with Google Takeout files (default: old)')
	parser.add_argument('--new-dir', default='new', help='Directory with Apple Photos exports (default: new)')
	parser.add_argument('--limit', type=int, help='Limit processing to specified number of files')
	parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
	parser.add_argument('--quiet', '-q', action='store_true', help='Suppress warning messages about missing files')
	parser.add_argument('--no-hash-matching', action='store_true', help='Disable image hash matching (faster but less accurate)')
	parser.add_argument('--similarity', type=float, default=0.98, help='Similarity threshold for image matching (0.0-1.0, default: 0.98)')
	parser.add_argument('--processed-log', default=os.path.join(data_dir, 'processed_files.csv'), help='Log file for processed files')
	parser.add_argument('--failed-updates-log', default=os.path.join(data_dir, 'failed_updates.csv'), help='Log file for failed metadata updates')
	parser.add_argument('--duplicates-log', default=os.path.join(data_dir, 'duplicates.csv'), help='Log file for duplicates')
	parser.add_argument('--rename-suffix', default=' (1)', help='Suffix to remove from filenames (default: " (1)")')
	parser.add_argument('--status-log', default=os.path.join(data_dir, 'metadata_status.csv'), help='Log file for metadata status (default: data/metadata_status.csv)')
	parser.add_argument('--import-to-photos', action='store_true', help='Import photos to Apple Photos after fixing metadata')
	parser.add_argument('--import-with-albums', action='store_true', help='Import photos to Apple Photos and organize them into albums based on Google Takeout structure')
	
	# Advanced options (hidden by default, for specific use cases)
	advanced_group = parser.add_argument_group('Advanced options', 'These options are for specific use cases and not needed for normal operation')
	advanced_group.add_argument('--skip-copy', action='store_true', help='Skip copying files from old directory to new directory')
	advanced_group.add_argument('--skip-duplicates', action='store_true', help='Skip finding and removing duplicates')
	advanced_group.add_argument('--skip-metadata', action='store_true', help='Skip applying metadata')
	advanced_group.add_argument('--find-duplicates-only', action='store_true', help='Only find and report duplicates without updating metadata')
	advanced_group.add_argument('--copy-to-new', action='store_true', help='Only copy files from old directory to new directory')
	advanced_group.add_argument('--remove-duplicates', action='store_true', help='Only remove duplicate files in the new directory')
	advanced_group.add_argument('--rename-files', action='store_true', help='Only rename files by removing "(1)" from filenames')
	advanced_group.add_argument('--fix-metadata', action='store_true', help='Fix metadata for problematic file types (MPG, AVI, PNG, AAE)')
	advanced_group.add_argument('--extensions', type=str, help='Comma-separated list of file extensions to process (e.g., "mpg,avi,png")')
	advanced_group.add_argument('--overwrite', action='store_true', help='Overwrite existing XMP sidecar files')
	advanced_group.add_argument('--find-duplicates-by-name', action='store_true', help='Find duplicates by checking for files with the same base name but with "(1)" suffix')
	advanced_group.add_argument('--name-duplicates-log', default=os.path.join(data_dir, 'name_duplicates.csv'), help='Log file for name-based duplicates (default: data/name_duplicates.csv)')
	advanced_group.add_argument('--check-metadata', action='store_true', help='Check which files in the new directory need metadata updates from the old directory')
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
	
	# If fix-metadata flag is set, run the fix_metadata function
	if args.fix_metadata:
		return fix_metadata(args)
	
	if args.dry_run:
		logger.info("Performing dry run (no files will be modified)")
	
	# Set up the processed files and failed updates loggers
	MetadataService.setup_processed_files_logger(args.processed_log, args.failed_updates_log)
	
	# Handle specific advanced options first
	if args.find_duplicates_only:
		from src.utils.image_utils import find_duplicates
		logger.info(f"Finding duplicates in {new_dir}...")
		duplicates = find_duplicates(new_dir, args.similarity)
		if duplicates:
			dup_count = sum(len(dups) for dups in duplicates.values())
			logger.info(f"Found {dup_count} duplicate files in {len(duplicates)} groups")
			logger.info(f"Results written to {args.duplicates_log}")
		else:
			logger.info("No duplicates found")
		
	if args.check_metadata:
		from src.utils.image_utils import check_metadata_status
		logger.info(f"Checking metadata status for files in {new_dir}...")
		total, with_metadata, without_metadata = check_metadata_status(old_dir, new_dir, args.status_log)
		logger.info(f"Total files in {new_dir}: {total}")
		logger.info(f"Files with metadata available: {with_metadata} ({with_metadata/total*100:.1f}%)")
		logger.info(f"Files without metadata: {without_metadata} ({without_metadata/total*100:.1f}%)")
		logger.info(f"Detailed status written to {args.status_log}")
		
	if args.find_duplicates_by_name:
		from src.utils.image_utils import find_duplicates_by_name
		logger.info(f"Finding duplicates by name in {new_dir}...")
		found, removed = find_duplicates_by_name(new_dir, args.rename_suffix, args.dry_run, args.name_duplicates_log)
		if args.dry_run:
			logger.info(f"[DRY RUN] Would remove {found} duplicate files")
		else:
			logger.info(f"Removed {removed} of {found} duplicate files")
		
	if args.rename_files:
		from src.utils.image_utils import rename_files_remove_suffix
		logger.info(f"Renaming files in {new_dir} by removing '{args.rename_suffix}' suffix...")
		processed, renamed = rename_files_remove_suffix(new_dir, args.rename_suffix, args.dry_run)
		if args.dry_run:
			logger.info(f"[DRY RUN] Would rename {renamed} of {processed} files")
		else:
			logger.info(f"Renamed {renamed} of {processed} files")
		
	if args.copy_to_new:
		logger.info(f"Copying missing media files from {old_dir} to {new_dir}...")
		missing_count, copied_count = CopyService.copy_missing_files(old_dir, new_dir, args.dry_run)
		if args.dry_run:
			logger.info(f"[DRY RUN] Would copy {copied_count} of {missing_count} missing files from {old_dir} to {new_dir}")
		else:
			logger.info(f"Finished copying files. Copied {copied_count} of {missing_count} missing files from {old_dir} to {new_dir}")
		
	if args.remove_duplicates:
		from src.utils.image_utils import remove_duplicates
		logger.info(f"Removing duplicates in {new_dir} based on {args.duplicates_log}...")
		if not os.path.exists(args.duplicates_log):
			logger.error(f"Duplicates log file not found: {args.duplicates_log}")
			logger.info("Run the script with --find-duplicates-only first to generate the duplicates log")
			return 1
		processed, removed = remove_duplicates(args.duplicates_log, args.dry_run)
		if args.dry_run:
			logger.info(f"[DRY RUN] Would remove {removed} of {processed} duplicate files")
		else:
			logger.info(f"Removed {removed} of {processed} duplicate files")
		
	# Default workflow: copy -> find duplicates -> remove duplicates -> apply metadata
	# Step 1: Copy missing files from old to new (if not skipped)
	if not args.skip_copy:
		logger.info(f"Step 1/3: Copying missing media files from {old_dir} to {new_dir}...")
		missing_count, copied_count = CopyService.copy_missing_files(old_dir, new_dir, args.dry_run)
		if args.dry_run:
			logger.info(f"[DRY RUN] Would copy {copied_count} of {missing_count} missing files from {old_dir} to {new_dir}")
		else:
			logger.info(f"Finished copying files. Copied {copied_count} of {missing_count} missing files from {old_dir} to {new_dir}")
	
	# Step 2: Find and remove duplicates (if not skipped)
	if not args.skip_duplicates:
		logger.info(f"Step 2/3: Finding and removing duplicates in {new_dir}...")
		
		# Find duplicates
		from src.utils.image_utils import find_duplicates, remove_duplicates
		duplicates = find_duplicates(new_dir, args.similarity)
		
		if duplicates:
			dup_count = sum(len(dups) for dups in duplicates.values())
			logger.info(f"Found {dup_count} duplicate files in {len(duplicates)} groups")
			logger.info(f"Results written to {args.duplicates_log}")
			
			# Remove duplicates
			processed, removed = remove_duplicates(args.duplicates_log, args.dry_run)
			
			if args.dry_run:
				logger.info(f"[DRY RUN] Would remove {removed} of {processed} duplicate files")
			else:
				logger.info(f"Removed {removed} of {processed} duplicate files")
		else:
			logger.info("No duplicates found")
	else:
		logger.info("Step 2/3: Skipping duplicate search and removal (--skip-duplicates)")

	# Step 3: Apply metadata (if not skipped)
	if not args.skip_metadata:
		logger.info(f"Step 3/3: Applying metadata from {old_dir} to files in {new_dir}...")
		
		# Двухэтапная обработка: сначала по JSON, потом по остальным файлам
		from pathlib import Path
		
		processed_files = set()

		# Optimized reporting: only matched and processed files are counted
		logger.info("Finding matched media/JSON pairs...")
		matched_pairs = MetadataService.find_metadata_pairs(old_dir, new_dir)
		total_matched = len(matched_pairs)
		updated_count = 0
		failed_count = 0
		for i, (json_path, media_file, _) in enumerate(matched_pairs, 1):
			try:
				if i % 10 == 0 or i == total_matched:
					logger.info(f"Progress: {i}/{total_matched} matched files processed")
				if process_file(media_file, old_dir, args.dry_run, args.overwrite):
					updated_count += 1
				else:
					failed_count += 1
			except KeyboardInterrupt:
				logger.warning("Process interrupted by user")
				break
			except Exception as e:
				logger.error(f"Error processing {media_file}: {str(e)}")
				failed_count += 1
	
	elapsed_time = time.time() - start_time
	minutes, seconds = divmod(elapsed_time, 60)
	logger.info("=" * 50)
	logger.info("Metadata Synchronization Summary:")
	logger.info(f"Time elapsed: {int(minutes)} minutes, {int(seconds)} seconds")
	logger.info(f"Matched files: {total_matched}")
	logger.info(f"Updated: {updated_count}")
	logger.info(f"Failed: {failed_count}")
	if failed_count > 0:
		logger.info(f"Failed updates are logged in: {args.failed_updates_log}")
	logger.info(f"Detailed processing log: {args.processed_log}")
	logger.info("=" * 50)
	if updated_count > 0:
		logger.info("✅ Metadata synchronization completed successfully!")
	else:
		logger.info("❌ No files were successfully updated.")
	# Import to Apple Photos if requested (unchanged)
	if updated_count > 0 and (args.import_to_photos or args.import_with_albums):
		from src.services.photos_app_service import PhotosAppService
		logger.info("Importing photos to Apple Photos...")
		if args.import_with_albums:
			logger.info("Organizing photos into albums based on Google Takeout structure...")
			imported, skipped = PhotosAppService.import_photos_from_directory(old_dir, with_albums=True)
			logger.info(f"Import with albums complete. Imported: {imported}, Already in library: {skipped}")
		else:
			imported_count = 0
			skipped_count = 0
			logger.info("You can now import the files from the 'new' directory into Apple Photos.")
	else:
		logger.warning("⚠️ No files were successfully updated.")
	


if __name__ == '__main__':
	sys.exit(main())
