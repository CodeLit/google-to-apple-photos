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
	logger.info(f"Processing {file_path}")
	
	# Find corresponding JSON metadata
	metadata = find_json_metadata(file_path, old_dir)
	if not metadata:
		logger.warning(f"No metadata found for {file_path}")
		return False
	
	# Get file extension
	file_ext = os.path.splitext(file_path)[1].lower()
	
	# For video files and other problematic formats, create XMP sidecar
	if file_ext in ['.mpg', '.avi', '.png', '.aae']:
		return create_xmp_sidecar(file_path, metadata, dry_run, overwrite)
	else:
		# For other file types, try direct update first
		success = update_file_metadata(file_path, metadata, dry_run)
		if not success:
			# If direct update fails, try sidecar as fallback
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
	
	# Validate directories
	if not os.path.isdir(args.old_dir):
		logger.error(f"Old directory not found: {args.old_dir}")
		return 1
	
	if not os.path.isdir(args.new_dir):
		logger.error(f"New directory not found: {args.new_dir}")
		return 1
	
	# Find files to process
	files_to_process = []
	
	if args.failed_updates_log and os.path.isfile(args.failed_updates_log):
		# Process files from the failed log
		try:
			import csv
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
				
				files_to_process = list(file_paths)
			logger.info(f"Found {len(files_to_process)} files in failed updates log")
		except Exception as e:
			logger.error(f"Error reading failed updates log: {str(e)}")
			return 1
	elif args.extensions:
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
	
	for i, file_path in enumerate(files_to_process):
		if (i + 1) % 10 == 0 or i + 1 == len(files_to_process):
			logger.info(f"Progress: {i+1}/{len(files_to_process)} files processed")
		
		try:
			result = "failure"
			if process_file(file_path, args.old_dir, args.dry_run, args.overwrite):
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
	
	return 0


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
	parser.add_argument('--processed-log', default=os.path.join(data_dir, 'processed_files.csv'), help='Log file for processed files')
	parser.add_argument('--failed-updates-log', default=os.path.join(data_dir, 'failed_updates.csv'), help='Log file for failed metadata updates')
	parser.add_argument('--copy-to-new', action='store_true', help='Copy files from old directory to new directory before processing')
	parser.add_argument('--remove-duplicates', action='store_true', help='Remove duplicate files in the new directory based on duplicates.log')
	parser.add_argument('--duplicates-log', default=os.path.join(data_dir, 'duplicates.csv'), help='Log file for duplicates')
	parser.add_argument('--rename-files', action='store_true', help='Rename files by removing "(1)" from filenames')
	parser.add_argument('--fix-metadata', action='store_true', help='Fix metadata for problematic file types (MPG, AVI, PNG, AAE)')
	parser.add_argument('--extensions', type=str, help='Comma-separated list of file extensions to process (e.g., "mpg,avi,png")')
	parser.add_argument('--overwrite', action='store_true', help='Overwrite existing XMP sidecar files')
	parser.add_argument('--rename-suffix', default=' (1)', help='Suffix to remove from filenames (default: " (1)")')
	parser.add_argument('--find-duplicates-by-name', action='store_true', help='Find duplicates by checking for files with the same base name but with "(1)" suffix')
	parser.add_argument('--name-duplicates-log', default=os.path.join(data_dir, 'name_duplicates.csv'), help='Log file for name-based duplicates (default: data/name_duplicates.csv)')
	parser.add_argument('--check-metadata', action='store_true', help='Check which files in the new directory need metadata updates from the old directory')
	parser.add_argument('--status-log', default=os.path.join(data_dir, 'metadata_status.csv'), help='Log file for metadata status (default: data/metadata_status.csv)')
	parser.add_argument('--import-to-photos', action='store_true', help='Import photos to Apple Photos after fixing metadata')
	parser.add_argument('--import-with-albums', action='store_true', help='Import photos to Apple Photos and organize them into albums based on Google Takeout structure')
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
	
	# Copy files from old to new if requested
	if args.copy_to_new:
		logger.info(f"Copying missing media files from {old_dir} to {new_dir}...")
		
		# Use the new CopyService to copy missing files
		missing_count, copied_count = CopyService.copy_missing_files(old_dir, new_dir, args.dry_run)
		
		if args.dry_run:
			logger.info(f"[DRY RUN] Would copy {copied_count} of {missing_count} missing files from {old_dir} to {new_dir}")
		else:
			logger.info(f"Finished copying files. Copied {copied_count} of {missing_count} missing files from {old_dir} to {new_dir}")
	
	# Remove duplicates if requested
	if args.remove_duplicates:
		from src.utils.image_utils import remove_duplicates
		logger.info(f"Removing duplicates in {new_dir} based on {args.duplicates_log}...")
		
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
		from src.utils.image_utils import rename_files_remove_suffix
		logger.info(f"Renaming files in {new_dir} by removing '{args.rename_suffix}' suffix...")
		
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
		from src.utils.image_utils import check_metadata_status
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
		from src.utils.image_utils import find_duplicates_by_name
		logger.info(f"Finding duplicates by name in {new_dir}...")
		
		# Find and optionally remove duplicates by name
		found, removed = find_duplicates_by_name(new_dir, args.rename_suffix, args.dry_run, args.name_duplicates_log)
		
		# Print summary
		if args.dry_run:
			logger.info(f"[DRY RUN] Would remove {found} duplicate files")
		else:
			logger.info(f"Removed {removed} of {found} duplicate files")
		
		return 0
	
	# Find duplicates if requested
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
		return 0
	
	# Find metadata pairs
	logger.info(f"Scanning directories: {old_dir} -> {new_dir}")
	use_hash_matching = not args.no_hash_matching
	metadata_pairs = MetadataService.find_metadata_pairs(old_dir, new_dir, 
										use_hash_matching=not args.no_hash_matching, 
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
	logger.info(f"Duplicates report: data/duplicates.csv")
	logger.info("=" * 50)
	
	if success_count > 0:
		logger.info("✅ Metadata synchronization completed successfully!")
		
		# Import to Apple Photos if requested
		if args.import_to_photos or args.import_with_albums:
			from src.services.photos_app_service import PhotosAppService
			
			logger.info("Importing photos to Apple Photos...")
			
			if args.import_with_albums:
				logger.info("Organizing photos into albums based on Google Takeout structure...")
				imported, skipped = PhotosAppService.import_photos_from_directory(old_dir, with_albums=True)
				logger.info(f"Import with albums complete. Imported: {imported}, Already in library: {skipped}")
			else:
				# Import processed files only
				imported_count = 0
				skipped_count = 0
				processed_files = [pair[1] for pair in metadata_pairs]  # Get the new files that were processed
				
				for file_path in processed_files:
					# Get timestamp from metadata if available
					json_file = find_json_metadata(file_path, old_dir)
					timestamp = ""
					
					if json_file:
						timestamp = PhotosAppService.get_photo_timestamp(json_file)
					
					result = PhotosAppService.import_photo(file_path, timestamp)
					if result:
						skipped_count += 1
					else:
						imported_count += 1
				
				logger.info(f"Import complete. Imported: {imported_count}, Already in library: {skipped_count}")
		else:
			logger.info("You can now import the files from the 'new' directory into Apple Photos.")
	else:
		logger.warning("⚠️ No files were successfully updated.")
	
	return 0


if __name__ == '__main__':
	sys.exit(main())
