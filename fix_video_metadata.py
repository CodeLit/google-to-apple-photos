#!/usr/bin/env python3
"""
Script to fix metadata for video files (MPG, AVI) that exiftool can't directly modify
This script creates XMP sidecar files with the correct metadata
"""
import os
import sys
import logging
import csv
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.exiftool_service import ExifToolService
from src.models.metadata import PhotoMetadata
from src.services.metadata_service import MetadataService

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(),
		logging.FileHandler('fix_video_metadata.log')
	]
)
logger = logging.getLogger(__name__)

def create_xmp_sidecar(file_path, creation_date=None):
	"""
	Create an XMP sidecar file for a video file
	
	Args:
		file_path: Path to the video file
		creation_date: Creation date in YYYY:MM:DD HH:MM:SS format
		
	Returns:
		Path to the created sidecar file or None if failed
	"""
	try:
		# If no creation date provided, try to get it from the file system
		if not creation_date:
			try:
				creation_time = os.path.getctime(file_path)
				date_format = "%Y:%m:%d %H:%M:%S"
				creation_date = datetime.fromtimestamp(creation_time).strftime(date_format)
			except Exception as e:
				logger.warning(f"Could not get file creation time for {file_path}: {str(e)}")
				return None
		
		# Create XMP sidecar file
		sidecar_path = f"{file_path}.xmp"
		
		# Use exiftool to create the XMP sidecar
		cmd = [
			'exiftool',
			'-o', sidecar_path,  # Output to sidecar file
			f'-DateTimeOriginal={creation_date}',
			f'-CreateDate={creation_date}',
			f'-ModifyDate={creation_date}',
			'-xmp:all',  # Include all XMP metadata
			file_path
		]
		
		result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
		
		if result.returncode == 0:
			logger.info(f"Successfully created XMP sidecar for {file_path}")
			return sidecar_path
		else:
			logger.error(f"Failed to create XMP sidecar for {file_path}: {result.stderr}")
			return None
	except Exception as e:
		logger.error(f"Error creating XMP sidecar for {file_path}: {str(e)}")
		return None

def find_json_metadata(file_path, old_dir):
	"""
	Find the corresponding JSON metadata file in the old directory
	
	Args:
		file_path: Path to the video file
		old_dir: Directory with Google Takeout files
		
	Returns:
		PhotoMetadata object or None if not found
	"""
	try:
		# Get the base filename without extension
		base_name = os.path.splitext(os.path.basename(file_path))[0]
		
		# Look for JSON files with matching name
		for root, _, files in os.walk(old_dir):
			for file in files:
				if file.endswith('.json') and base_name in file:
					json_path = os.path.join(root, file)
					metadata = MetadataService.parse_json_metadata(json_path)
					if metadata:
						return metadata
		
		return None
	except Exception as e:
		logger.error(f"Error finding JSON metadata for {file_path}: {str(e)}")
		return None

def main():
	"""Main function to fix video metadata"""
	parser = argparse.ArgumentParser(description='Fix metadata for video files using XMP sidecars')
	parser.add_argument('--failed-log', default='failed_updates.log', help='Log file with failed updates (default: failed_updates.log)')
	parser.add_argument('--old-dir', default='old', help='Directory with Google Takeout files (default: old)')
	parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without creating any files')
	parser.add_argument('--limit', type=int, help='Limit processing to specified number of files')
	args = parser.parse_args()
	
	# Check if exiftool is installed
	if not ExifToolService.check_exiftool():
		return 1
	
	# Check if the failed updates log exists
	if not os.path.exists(args.failed_log):
		logger.error(f"Failed updates log not found: {args.failed_log}")
		return 1
	
	# Get absolute path for old directory
	script_dir = os.path.dirname(os.path.abspath(__file__))
	old_dir = os.path.join(script_dir, args.old_dir)
	
	# Read the failed updates log
	video_files = []
	try:
		with open(args.failed_log, 'r') as f:
			reader = csv.reader(f)
			# Skip header
			next(reader, None)
			# Get unique video file paths
			file_paths = set()
			for row in reader:
				if row and len(row) >= 1:
					file_path = row[0]
					# Check if it's a video file
					ext = os.path.splitext(file_path)[1].lower()
					if ext in ['.mpg', '.mpeg', '.avi', '.mp4', '.mov']:
						if os.path.exists(file_path):
							file_paths.add(file_path)
						else:
							logger.warning(f"File not found: {file_path}")
			
			video_files = list(file_paths)
	except Exception as e:
		logger.error(f"Error reading failed updates log: {str(e)}")
		return 1
	
	logger.info(f"Found {len(video_files)} video files that need metadata sidecars")
	
	# Limit processing if requested
	if args.limit and args.limit > 0 and args.limit < len(video_files):
		logger.info(f"Limiting processing to {args.limit} files")
		video_files = video_files[:args.limit]
	
	# Create output log file for fixed files
	fixed_log_path = 'fixed_video_files.log'
	with open(fixed_log_path, 'w') as fixed_log:
		fixed_log.write("file_path,sidecar_path,result,timestamp\n")
	
	# Process files
	success_count = 0
	failure_count = 0
	
	for i, file_path in enumerate(video_files, 1):
		try:
			# Log progress
			if i % 10 == 0 or i == len(video_files):
				logger.info(f"Progress: {i}/{len(video_files)} files processed")
			
			logger.info(f"Processing {file_path}")
			
			# Find corresponding JSON metadata
			metadata = find_json_metadata(file_path, old_dir)
			creation_date = None
			
			if metadata and metadata.date_taken:
				# Use the date from Google Takeout metadata
				creation_date = metadata.date_taken.strftime("%Y:%m:%d %H:%M:%S")
				logger.info(f"Found creation date from metadata: {creation_date}")
			
			if args.dry_run:
				logger.info(f"[DRY RUN] Would create XMP sidecar for {file_path}")
				result = "dry_run"
				sidecar_path = f"{file_path}.xmp"
			else:
				# Create XMP sidecar
				sidecar_path = create_xmp_sidecar(file_path, creation_date)
				
				if sidecar_path:
					logger.info(f"Created XMP sidecar: {sidecar_path}")
					success_count += 1
					result = "success"
				else:
					logger.error(f"Failed to create XMP sidecar for {file_path}")
					failure_count += 1
					result = "failure"
					sidecar_path = "none"
			
			# Log the result
			with open(fixed_log_path, 'a') as fixed_log:
				timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
				fixed_log.write(f"{file_path},{sidecar_path},{result},{timestamp}\n")
				
		except KeyboardInterrupt:
			logger.warning("Process interrupted by user")
			break
		except Exception as e:
			logger.error(f"Error processing {file_path}: {str(e)}")
			failure_count += 1
			
			# Log the error
			with open(fixed_log_path, 'a') as fixed_log:
				timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
				fixed_log.write(f"{file_path},none,error: {str(e)},{timestamp}\n")
	
	# Print summary
	logger.info("=" * 50)
	logger.info("Video Metadata Fix Summary:")
	logger.info(f"Total video files processed: {len(video_files)}")
	logger.info(f"Successfully created sidecars: {success_count} files")
	logger.info(f"Failed to create sidecars: {failure_count} files")
	logger.info(f"Results written to: {fixed_log_path}")
	logger.info("=" * 50)
	
	if success_count > 0:
		logger.info("✅ Video metadata fix completed!")
		logger.info("XMP sidecar files have been created alongside the video files.")
		logger.info("These will be recognized by Apple Photos when importing.")
	else:
		logger.warning("⚠️ No XMP sidecar files were successfully created.")
	
	return 0

if __name__ == '__main__':
	sys.exit(main())
