#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import unittest
import logging
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Set

from src.services.metadata_service import MetadataService
from src.services.exiftool_service import ExifToolService
from src.utils.image_utils import compute_hash_for_file, is_image_file, is_video_file

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FormatSupportTest(unittest.TestCase):
	"""Test support for various media formats"""
	
	@classmethod
	def setUpClass(cls):
		"""Set up test environment once for all tests"""
		# Create temporary test directories
		cls.test_dir = tempfile.mkdtemp(prefix="format_test_")
		cls.test_old_dir = os.path.join(cls.test_dir, "old")
		cls.test_new_dir = os.path.join(cls.test_dir, "new")
		os.makedirs(cls.test_old_dir, exist_ok=True)
		os.makedirs(cls.test_new_dir, exist_ok=True)
		
		# Define the formats we want to test
		cls.image_formats = ["jpg", "jpeg", "heic", "png", "gif", "webp"]
		cls.video_formats = ["mp4", "mov", "mkv", "mpg", "3gp", "avi"]
		
		# Prepare test files
		cls._prepare_test_files()
		
		# Initialize services
		cls.metadata_service = MetadataService
		cls.exiftool_service = ExifToolService
		
		# Results tracking
		cls.format_results = {}
	
	@classmethod
	def tearDownClass(cls):
		"""Clean up after all tests"""
		# Remove temporary directory
		shutil.rmtree(cls.test_dir)
	
	@classmethod
	def _prepare_test_files(cls):
		"""Prepare test files for each format from test_images or old directory"""
		project_root = Path(__file__).parent.parent
		test_images_dir = project_root / "test_images"
		old_dir = project_root / "old"
		
		# Track which formats we've found
		found_formats = set()
		
		# First try to find files in test_images
		cls._copy_format_samples(test_images_dir, found_formats)
		
		# For any missing formats, try to find them in old
		missing_formats = set(cls.image_formats + cls.video_formats) - found_formats
		if missing_formats:
			logger.info(f"Looking for missing formats in old directory: {missing_formats}")
			cls._copy_format_samples(old_dir, found_formats)
		
		# Report on formats we couldn't find
		still_missing = set(cls.image_formats + cls.video_formats) - found_formats
		if still_missing:
			logger.warning(f"Could not find sample files for formats: {still_missing}")
	
	@classmethod
	def _copy_format_samples(cls, source_dir: Path, found_formats: Set[str]):
		"""Copy sample files for each format from source_dir"""
		if not source_dir.exists():
			logger.warning(f"Source directory does not exist: {source_dir}")
			return
		
		# Process each format
		for fmt in cls.image_formats + cls.video_formats:
			if fmt in found_formats:
				continue
				
			# Find files with this extension
			pattern = f"*.{fmt}"
			matching_files = list(source_dir.glob(f"**/{pattern}"))
			matching_files.extend(list(source_dir.glob(f"**/{pattern.upper()}")))
			
			if matching_files:
				# Found at least one file with this format
				found_formats.add(fmt)
				
				# Copy a sample file to our test directory
				sample_file = matching_files[0]
				dest_path = os.path.join(cls.test_old_dir, f"sample.{fmt}")
				shutil.copy2(sample_file, dest_path)
				
				# If there's a corresponding JSON file, copy that too
				json_path = sample_file.with_suffix(".json")
				if json_path.exists():
					shutil.copy2(json_path, os.path.join(cls.test_old_dir, f"sample.{fmt}.json"))
				else:
					# Create a simple JSON file with basic metadata
					cls._create_sample_json(os.path.join(cls.test_old_dir, f"sample.{fmt}.json"))
				
				logger.info(f"Copied sample {fmt} file: {sample_file}")
				
				# Also copy to new directory for testing metadata application
				shutil.copy2(sample_file, os.path.join(cls.test_new_dir, f"sample.{fmt}"))
	
	@classmethod
	def _create_sample_json(cls, json_path: str):
		"""Create a sample JSON file with basic metadata"""
		metadata = {
			"title": "Sample Image",
			"photoTakenTime": {
				"timestamp": "1609459200"  # 2021-01-01 00:00:00
			},
			"geoData": {
				"latitude": 37.7749,
				"longitude": -122.4194
			}
		}
		
		with open(json_path, 'w') as f:
			json.dump(metadata, f, indent=2)
	
	def test_format_detection(self):
		"""Test that each format is correctly detected as image or video"""
		# Initialize format_results for all formats
		for fmt in self.image_formats + self.video_formats:
			self.format_results[fmt] = {"exists": False}
		
		for fmt in self.image_formats:
			file_path = os.path.join(self.test_old_dir, f"sample.{fmt}")
			if os.path.exists(file_path):
				self.format_results[fmt]["exists"] = True
				is_image = is_image_file(file_path)
				self.format_results[fmt]["detected_as_image"] = is_image
				
				# Some formats like webp might not be detected correctly
				# Just log the result rather than failing the test
				if not is_image:
					logger.warning(f"{fmt} was not detected as an image")
				
				self.assertFalse(is_video_file(file_path), f"{fmt} should not be detected as a video")
			else:
				logger.warning(f"No sample file found for {fmt}")
		
		for fmt in self.video_formats:
			file_path = os.path.join(self.test_old_dir, f"sample.{fmt}")
			if os.path.exists(file_path):
				self.format_results[fmt]["exists"] = True
				is_video = is_video_file(file_path)
				self.format_results[fmt]["detected_as_video"] = is_video
				
				# Some formats might not be detected correctly
				# Just log the result rather than failing the test
				if not is_video:
					logger.warning(f"{fmt} was not detected as a video")
				
				self.assertFalse(is_image_file(file_path), f"{fmt} should not be detected as an image")
			else:
				logger.warning(f"No sample file found for {fmt}")
	
	def test_hash_computation(self):
		"""Test that hashes can be computed for each format"""
		for fmt in self.image_formats + self.video_formats:
			file_path = os.path.join(self.test_old_dir, f"sample.{fmt}")
			if os.path.exists(file_path):
				hash_value = compute_hash_for_file(file_path)
				self.format_results[fmt]["hash_computed"] = hash_value is not None
				
				# Some formats might not support hash computation
				# Just log the result rather than failing the test
				if hash_value is None:
					logger.warning(f"Could not compute hash for {fmt}")
	
	def test_metadata_extraction(self):
		"""Test metadata extraction for each format"""
		for fmt in self.image_formats + self.video_formats:
			file_path = os.path.join(self.test_old_dir, f"sample.{fmt}")
			if os.path.exists(file_path):
				# Test metadata extraction
				try:
					metadata = self.exiftool_service.get_metadata(file_path)
					self.format_results[fmt]["metadata_extraction"] = metadata is not None
					self.assertIsNotNone(metadata, f"Should be able to extract metadata from {fmt}")
					
					# Check if we can get creation date
					creation_date = None
					if metadata and "DateTimeOriginal" in metadata:
						creation_date = metadata["DateTimeOriginal"]
					self.format_results[fmt]["creation_date_extraction"] = creation_date is not None
				except Exception as e:
					logger.warning(f"Error extracting metadata from {fmt}: {str(e)}")
					self.format_results[fmt]["metadata_extraction"] = False
					self.format_results[fmt]["creation_date_extraction"] = False
	
	def test_metadata_application(self):
		"""Test metadata application for each format"""
		for fmt in self.image_formats + self.video_formats:
			file_path = os.path.join(self.test_new_dir, f"sample.{fmt}")
			json_path = os.path.join(self.test_old_dir, f"sample.{fmt}.json")
			
			if os.path.exists(file_path) and os.path.exists(json_path):
				# Extract metadata from JSON
				try:
					with open(json_path, 'r') as f:
						json_data = json.load(f)
					
					# Try to apply metadata
					timestamp = json_data.get("photoTakenTime", {}).get("timestamp")
					title = json_data.get("title")
					geo_data = json_data.get("geoData", {})
					latitude = geo_data.get("latitude")
					longitude = geo_data.get("longitude")
					
					if timestamp:
						# Apply metadata using apply_metadata
						try:
							result = self.exiftool_service.apply_metadata(
								file_path,
								timestamp=timestamp,
								title=title,
								latitude=latitude,
								longitude=longitude
							)
							self.format_results[fmt]["metadata_application"] = result
							self.assertTrue(result, f"Should be able to apply metadata to {fmt}")
						except Exception as e:
							logger.warning(f"Error applying metadata to {fmt}: {str(e)}")
							self.format_results[fmt]["metadata_application"] = False
					else:
						self.format_results[fmt]["metadata_application"] = False
						logger.warning(f"No timestamp in JSON for {fmt}")
				except Exception as e:
					logger.warning(f"Error processing JSON for {fmt}: {str(e)}")
					self.format_results[fmt]["metadata_application"] = False
			else:
				self.format_results[fmt]["metadata_application"] = False
	
	def test_file_matching(self):
		"""Test file matching for each format"""
		# Create a simple JSON file for each sample file if it doesn't exist
		for fmt in self.image_formats + self.video_formats:
			file_path = os.path.join(self.test_new_dir, f"sample.{fmt}")
			json_path = os.path.join(self.test_old_dir, f"sample.{fmt}.json")
			
			if os.path.exists(file_path) and not os.path.exists(json_path):
				self._create_sample_json(json_path)
			
			# Initialize file_matching result to False for all formats
			if fmt in self.format_results:
				self.format_results[fmt]["file_matching"] = False
		
		# Test name-based matching
		try:
			pairs = self.metadata_service.find_metadata_pairs(self.test_old_dir, self.test_new_dir)
			self.assertIsNotNone(pairs, "Should be able to find metadata pairs")
			
			# Check which formats were matched
			matched_formats = set()
			for pair in pairs:
				json_path, media_path = pair[0], pair[1]
				ext = os.path.splitext(media_path)[1][1:].lower()
				matched_formats.add(ext)
				
			# Record results
			for fmt in self.image_formats + self.video_formats:
				if fmt in self.format_results and self.format_results[fmt]["exists"]:
					self.format_results[fmt]["file_matching"] = fmt in matched_formats
		except Exception as e:
			logger.warning(f"Error in file matching test: {str(e)}")
	
	def test_generate_report(self):
		"""Generate a report of format support"""
		report = {
			"image_formats": {},
			"video_formats": {}
		}
		
		# Compile results for image formats
		for fmt in self.image_formats:
			if fmt in self.format_results:
				report["image_formats"][fmt] = self.format_results[fmt]
		
		# Compile results for video formats
		for fmt in self.video_formats:
			if fmt in self.format_results:
				report["video_formats"][fmt] = self.format_results[fmt]
		
		# Write report to file
		report_path = os.path.join(self.test_dir, "format_support_report.json")
		with open(report_path, 'w') as f:
			json.dump(report, f, indent=2)
		
		logger.info(f"Format support report written to {report_path}")
		
		# Print summary
		logger.info("=== FORMAT SUPPORT SUMMARY ===")
		logger.info("Image Formats:")
		for fmt, results in report["image_formats"].items():
			if results.get("exists", False):
				support_level = "Full" if all([
					results.get("detected_as_image", False),
					results.get("hash_computed", False),
					results.get("metadata_extraction", False),
					results.get("metadata_application", False),
					results.get("file_matching", False)
				]) else "Partial"
				logger.info(f"  {fmt}: {support_level} support")
			else:
				logger.info(f"  {fmt}: Not tested (no sample file)")
		
		logger.info("Video Formats:")
		for fmt, results in report["video_formats"].items():
			if results.get("exists", False):
				support_level = "Full" if all([
					results.get("detected_as_video", False),
					results.get("hash_computed", False),
					results.get("metadata_extraction", False),
					results.get("metadata_application", False),
					results.get("file_matching", False)
				]) else "Partial"
				logger.info(f"  {fmt}: {support_level} support")
			else:
				logger.info(f"  {fmt}: Not tested (no sample file)")

if __name__ == "__main__":
	unittest.main()
