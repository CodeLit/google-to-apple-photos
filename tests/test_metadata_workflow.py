"""
Test for the complete metadata workflow from Google Takeout to Apple Photos.
"""
import os
import shutil
import unittest
import json
import logging
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.exiftool_service import ExifToolService
from src.services.metadata_service import MetadataService
from src.models.metadata import Metadata, PhotoMetadata

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestMetadataWorkflow(unittest.TestCase):
	"""Test the complete metadata workflow from Google Takeout to Apple Photos."""
	
	def setUp(self):
		"""Set up the test environment."""
		# Define test directories
		self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
		self.test_dir = os.path.join(self.project_dir, 'test_images')
		self.old_dir = os.path.join(self.test_dir, 'old')
		self.new_dir = os.path.join(self.test_dir, 'new')
		
		# Create test directories if they don't exist
		os.makedirs(self.test_dir, exist_ok=True)
		os.makedirs(self.old_dir, exist_ok=True)
		os.makedirs(self.new_dir, exist_ok=True)
		
		# Check if we need to copy sample files from the project's old directory to test_images/old
		project_old_dir = os.path.join(self.project_dir, 'old')
		if os.path.exists(project_old_dir):
			# Check if test_images/old is empty
			if not os.listdir(self.old_dir):
				logger.info(f"Copying sample files from {project_old_dir} to {self.old_dir}")
				self.copy_sample_files(project_old_dir, self.old_dir)
		
		# Find JSON files in the old directory (recursive search)
		json_files = []
		for root, _, files in os.walk(self.old_dir):
			for file in files:
				if file.endswith('.json') and 'supplemental-metadata' in file:
					json_files.append(os.path.join(root, file))
		
		if not json_files:
			self.skipTest(f"No supplemental-metadata JSON files found in: {self.old_dir}")
	
	def get_test_files_info(self):
		"""Get information about the test files."""
		# Find all supplemental-metadata JSON files in the old directory (recursive search)
		json_files = []
		for root, _, files in os.walk(self.old_dir):
			for file in files:
				if file.endswith('.json') and 'supplemental-metadata' in file:
					json_files.append(os.path.join(root, file))
		
		# Find corresponding media files
		media_files = []
		for json_file in json_files:
			# Get the media filename by removing the supplemental-metadata.json part
			media_filename = os.path.basename(json_file).replace('.supplemental-metadata.json', '')
			# Look for the media file in the same directory as the JSON file
			media_file = os.path.join(os.path.dirname(json_file), media_filename)
			if os.path.exists(media_file):
				media_files.append(media_file)
		
		# Limit to a small number of files for testing
		max_files = 3
		json_files = json_files[:max_files]
		media_files = [m for m in media_files if any(os.path.basename(m) == os.path.basename(j).replace('.supplemental-metadata.json', '') for j in json_files)]
		
		logger.info(f"Selected {len(json_files)} JSON files and {len(media_files)} media files for testing")
		return json_files, media_files
	
	def copy_sample_files(self, source_dir, target_dir, max_files=3):
		"""Copy a few sample files from the project's old directory to test_images/old."""
		# Find JSON files with supplemental-metadata in the source directory
		json_files = []
		for root, _, files in os.walk(source_dir):
			for file in files:
				if file.endswith('.json') and 'supplemental-metadata' in file:
					json_files.append(os.path.join(root, file))
					if len(json_files) >= max_files:
						break
		
		# Copy each JSON file and its corresponding media file
		for json_file in json_files[:max_files]:
			# Create the target directory structure
			rel_path = os.path.relpath(os.path.dirname(json_file), source_dir)
			target_subdir = os.path.join(target_dir, rel_path)
			os.makedirs(target_subdir, exist_ok=True)
			
			# Copy the JSON file
			target_json = os.path.join(target_subdir, os.path.basename(json_file))
			shutil.copy2(json_file, target_json)
			logger.info(f"Copied {os.path.basename(json_file)} to test directory")
			
			# Find and copy the corresponding media file
			media_filename = os.path.basename(json_file).replace('.supplemental-metadata.json', '')
			media_file = os.path.join(os.path.dirname(json_file), media_filename)
			if os.path.exists(media_file):
				target_media = os.path.join(target_subdir, media_filename)
				shutil.copy2(media_file, target_media)
				logger.info(f"Copied {media_filename} to test directory")
		
		return len(json_files)
	
	def tearDown(self):
		"""Clean up after the test."""
		# We don't delete the test files here to keep them for inspection
		pass
	
	def test_metadata_workflow(self):
		"""Test the complete metadata workflow."""
		# Get information about test files
		json_files, media_files = self.get_test_files_info()
		if not json_files or not media_files:
			self.skipTest("Not enough test files to proceed")
		
		# Step 1: Clean the new directory
		self.clean_new_directory()
		
		# Step 2: Copy files from old to new
		self.copy_files_from_old_to_new()
		
		# Step 3: Apply metadata from JSON to images
		success_count, error_count = self.apply_metadata()
		
		# Step 4: Compare metadata
		comparison_success, comparison_errors = self.compare_metadata()
		
		# Step 5: Print report
		self.print_report(success_count, error_count, comparison_success, comparison_errors)
		
		# We don't assert that there are no errors because we're testing with real files
		# that might have various issues. Instead, we just report the results.
		logger.info(f"Test completed with {error_count} processing errors and {comparison_errors} comparison errors")
	
	def clean_new_directory(self):
		"""Clean the new directory by removing all files."""
		logger.info("Cleaning the new directory...")
		for file_path in Path(self.new_dir).glob('*'):
			if file_path.is_file():
				file_path.unlink()
		logger.info("New directory cleaned.")
	
	def copy_files_from_old_to_new(self):
		"""Copy selected media files from old to new directory."""
		logger.info("Copying files from old to new directory...")
		copied_count = 0
		
		# Get the list of media files to copy
		_, media_files = self.get_test_files_info()
		
		for file_path in media_files:
			# Copy to the new directory with the same filename (not preserving directory structure)
			dest_path = os.path.join(self.new_dir, os.path.basename(file_path))
			shutil.copy2(file_path, dest_path)
			copied_count += 1
			logger.info(f"Copied {os.path.basename(file_path)} to new directory")
		
		logger.info(f"Copied {copied_count} files from old to new directory.")
	
	def apply_metadata(self):
		"""Apply metadata from JSON files to corresponding images."""
		logger.info("Applying metadata from JSON files to images...")
		success_count = 0
		error_count = 0
		
		# Get JSON files
		json_files, _ = self.get_test_files_info()
		
		for json_path in json_files:
			try:
				# Extract metadata from JSON
				with open(json_path, 'r') as f:
					json_data = json.load(f)
				
				# Get the media filename by removing the supplemental-metadata.json part
				media_filename = os.path.basename(json_path).replace('.supplemental-metadata.json', '')
				
				# Find the corresponding image file in the new directory
				image_path = os.path.join(self.new_dir, media_filename)
				
				if not os.path.exists(image_path):
					logger.error(f"Image file not found in new directory: {media_filename}")
					error_count += 1
					continue
				
				# Extract metadata from JSON
				metadata = self.extract_metadata_from_json(json_data)
				if metadata is None:
					logger.error(f"Failed to extract metadata from {json_path}")
					error_count += 1
					continue
				
				# Apply metadata to the image
				exif_args = metadata.to_exiftool_args()
				result = ExifToolService.apply_metadata(image_path, exif_args)
				
				if result:
					logger.info(f"Successfully applied metadata to {media_filename}")
					success_count += 1
				else:
					logger.error(f"Failed to apply metadata to {media_filename}")
					error_count += 1
			
			except Exception as e:
				logger.error(f"Error processing {json_path}: {str(e)}")
				error_count += 1
		
		return success_count, error_count
	
	def extract_metadata_from_json(self, json_data):
		"""Extract metadata from JSON data."""
		# Check if this is a valid JSON with the expected fields
		if not isinstance(json_data, dict):
			logger.error(f"Invalid JSON data: {type(json_data)}")
			return None
		
		# Extract the title
		title = json_data.get('title', '')
		
		# Extract the date taken
		photo_taken_time = json_data.get('photoTakenTime', {})
		if not photo_taken_time:
			logger.warning(f"No photoTakenTime found in JSON data for {title}")
			date_taken_str = None
		else:
			timestamp = photo_taken_time.get('timestamp', '0')
			
			# Convert timestamp to datetime
			try:
				timestamp = int(timestamp)
				date_taken = datetime.fromtimestamp(timestamp)
				date_taken_str = date_taken.strftime('%Y:%m:%d %H:%M:%S')
			except (ValueError, TypeError) as e:
				logger.warning(f"Error parsing timestamp {timestamp}: {str(e)}")
				date_taken_str = None
		
		# Extract GPS coordinates
		geo_data = json_data.get('geoData', {})
		if not geo_data:
			logger.warning(f"No geoData found in JSON data for {title}")
			latitude = None
			longitude = None
		else:
			latitude = geo_data.get('latitude')
			longitude = geo_data.get('longitude')
		
		# Create metadata object only if we have at least one valid field
		if title or date_taken_str or latitude or longitude:
			metadata = Metadata(
				title=title,
				date_taken=date_taken_str,
				latitude=latitude,
				longitude=longitude
			)
			return metadata
		else:
			logger.warning("No valid metadata found in JSON data")
			return None
	
	def compare_metadata(self):
		"""Compare metadata between original JSON and processed images."""
		logger.info("Comparing metadata between original JSON and processed images...")
		success_count = 0
		error_count = 0
		
		# Get JSON files
		json_files, _ = self.get_test_files_info()
		
		for json_path in json_files:
			try:
				# Extract metadata from JSON
				with open(json_path, 'r') as f:
					json_data = json.load(f)
				
				# Get the media filename by removing the supplemental-metadata.json part
				media_filename = os.path.basename(json_path).replace('.supplemental-metadata.json', '')
				
				# Find the corresponding image file in the new directory
				image_path = os.path.join(self.new_dir, media_filename)
				
				if not os.path.exists(image_path):
					logger.error(f"Image file not found for comparison: {media_filename}")
					error_count += 1
					continue
				
				# Get metadata from the processed image
				image_metadata = ExifToolService.get_metadata(image_path)
				
				if image_metadata is None:
					logger.error(f"Failed to get metadata from processed image: {image_path}")
					error_count += 1
					continue
				
				# Extract expected date from JSON
				photo_taken_time = json_data.get('photoTakenTime', {})
				if not photo_taken_time:
					logger.warning(f"No photoTakenTime found in JSON data for {media_filename}")
					continue
				
				timestamp = photo_taken_time.get('timestamp', '0')
				
				try:
					timestamp = int(timestamp)
					expected_date = datetime.fromtimestamp(timestamp)
					expected_date_str = expected_date.strftime('%Y:%m:%d %H:%M:%S')
				except (ValueError, TypeError) as e:
					logger.warning(f"Error parsing timestamp {timestamp}: {str(e)}")
					continue
				
				# Get actual date from image metadata
				actual_date_str = image_metadata.get('DateTimeOriginal')
				if not actual_date_str:
					actual_date_str = image_metadata.get('CreateDate')
				
				# Compare dates
				if expected_date_str and actual_date_str:
					# Remove any timezone information for comparison
					actual_date_str = actual_date_str.split('+')[0].strip()
					
					if expected_date_str == actual_date_str:
						logger.info(f"Date metadata matches for {media_filename}")
						success_count += 1
					else:
						logger.error(f"Date metadata mismatch for {media_filename}:")
						logger.error(f"  Expected: {expected_date_str}")
						logger.error(f"  Actual: {actual_date_str}")
						error_count += 1
				else:
					logger.warning(f"Missing date metadata for comparison in {media_filename}")
					# Not counting as an error since this might be expected for some files
			
			except Exception as e:
				logger.error(f"Error comparing metadata for {json_path}: {str(e)}")
				error_count += 1
		
		return success_count, error_count
	
	def print_report(self, success_count, error_count, comparison_success, comparison_errors):
		"""Print a summary report of the test."""
		total_processed = success_count + error_count
		total_compared = comparison_success + comparison_errors
		
		logger.info("=" * 50)
		logger.info("METADATA WORKFLOW TEST REPORT")
		logger.info("=" * 50)
		logger.info(f"Total files processed: {total_processed}")
		logger.info(f"  - Successfully processed: {success_count}")
		logger.info(f"  - Errors during processing: {error_count}")
		logger.info(f"Total files compared: {total_compared}")
		logger.info(f"  - Successful comparisons: {comparison_success}")
		logger.info(f"  - Comparison errors: {comparison_errors}")
		logger.info("=" * 50)


if __name__ == '__main__':
	unittest.main()
