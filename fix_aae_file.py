#!/usr/bin/env python3
"""
Script to handle AAE file metadata
AAE files are Apple's edit information files and require special handling
"""
import os
import sys
import logging
import subprocess
from datetime import datetime

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(),
		logging.FileHandler('fix_aae_file.log')
	]
)
logger = logging.getLogger(__name__)

def main():
	"""Handle the AAE file metadata"""
	# Path to the AAE file
	aae_file = "/Users/nlit/projects/google-to-apple-photos/new/IMG_O4152(1).aae"
	
	if not os.path.exists(aae_file):
		logger.error(f"AAE file not found: {aae_file}")
		return 1
	
	logger.info(f"Processing AAE file: {aae_file}")
	
	# Create a simple text sidecar file with metadata
	sidecar_path = f"{aae_file}.txt"
	
	try:
		# Get file creation time from filesystem
		creation_time = os.path.getctime(aae_file)
		modification_time = os.path.getmtime(aae_file)
		
		# Format dates
		date_format = "%Y-%m-%d %H:%M:%S"
		creation_date = datetime.fromtimestamp(creation_time).strftime(date_format)
		modify_date = datetime.fromtimestamp(modification_time).strftime(date_format)
		
		# Write metadata to sidecar file
		with open(sidecar_path, 'w') as f:
			f.write(f"Original AAE File: {os.path.basename(aae_file)}\n")
			f.write(f"Creation Date: {creation_date}\n")
			f.write(f"Modification Date: {modify_date}\n")
			f.write("Note: AAE files are Apple's edit information files and cannot have metadata embedded directly.\n")
			f.write("This sidecar file contains the original metadata for reference.\n")
		
		logger.info(f"Created text sidecar file: {sidecar_path}")
		
		# Try to create an XMP sidecar as well
		xmp_path = f"{aae_file}.xmp"
		
		# Use exiftool to create the XMP sidecar
		cmd = [
			'exiftool',
			'-o', xmp_path,
			f'-DateTimeOriginal={creation_date.replace("-", ":")}'
			f'-CreateDate={creation_date.replace("-", ":")}',
			f'-ModifyDate={modify_date.replace("-", ":")}',
			'-xmp:all',
			aae_file
		]
		
		try:
			result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
			if result.returncode == 0:
				logger.info(f"Successfully created XMP sidecar for {aae_file}")
			else:
				logger.warning(f"Could not create XMP sidecar, but text sidecar is available: {result.stderr}")
		except Exception as e:
			logger.warning(f"Error creating XMP sidecar: {str(e)}")
		
		return 0
	except Exception as e:
		logger.error(f"Error processing AAE file: {str(e)}")
		return 1

if __name__ == '__main__':
	sys.exit(main())
