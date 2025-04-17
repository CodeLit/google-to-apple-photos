#!/usr/bin/env python3
"""
Unit tests for exiftool_service module
"""
import os
import sys
import unittest
import tempfile
import subprocess
from unittest.mock import patch, MagicMock

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.exiftool_service import ExifToolService


class TestExifToolService(unittest.TestCase):
	"""Test cases for ExifToolService class"""

	def setUp(self):
		"""Set up test environment"""
		# Create a temporary directory for test files
		self.temp_dir = tempfile.TemporaryDirectory()
		self.test_dir = self.temp_dir.name

	def tearDown(self):
		"""Clean up test environment"""
		self.temp_dir.cleanup()

	@patch('subprocess.run')
	def test_check_exiftool_installed(self, mock_run):
		"""Test checking if exiftool is installed"""
		# Mock subprocess.run to simulate exiftool being installed
		mock_process = MagicMock()
		mock_process.returncode = 0
		mock_run.return_value = mock_process
		
		# Test the method
		result = ExifToolService.check_exiftool()
		
		# Verify the result
		self.assertTrue(result)
		
		# Verify that subprocess.run was called correctly
		mock_run.assert_called_once()

	@patch('subprocess.run')
	def test_check_exiftool_not_installed(self, mock_run):
		"""Test checking if exiftool is not installed"""
		# Mock subprocess.run to simulate exiftool not being installed
		mock_run.side_effect = FileNotFoundError("No such file or directory: 'exiftool'")
		
		# Test the method with assertLogs to capture the error message
		with self.assertLogs(level='ERROR') as log:
			result = ExifToolService.check_exiftool()
			
			# Verify that the error was logged
			self.assertIn("exiftool is not installed", log.output[0])
		
		# Verify the result
		self.assertFalse(result)

	@patch('subprocess.run')
	def test_detect_file_type_jpeg(self, mock_run):
		"""Test detecting JPEG file type"""
		# Create a test file
		test_file = os.path.join(self.test_dir, "test.jpg")
		with open(test_file, 'w') as f:
			f.write("test file content")
		
		# Mock subprocess.run to simulate exiftool output for JPEG
		mock_process = MagicMock()
		mock_process.returncode = 0
		mock_process.stdout = "JPEG"
		mock_run.return_value = mock_process
		
		# Test the method
		ext, mime = ExifToolService.detect_file_type(test_file)
		
		# Verify the result
		self.assertEqual(ext, "jpg")
		self.assertTrue(mime.startswith("image/"))

	@patch('subprocess.run')
	def test_detect_file_type_nonexistent_file(self, mock_run):
		"""Test detecting file type for a nonexistent file"""
		# Test with a nonexistent file
		nonexistent_file = os.path.join(self.test_dir, "nonexistent.jpg")
		
		# Test the method
		ext, mime = ExifToolService.detect_file_type(nonexistent_file)
		
		# Verify the result
		self.assertEqual(ext, "")
		self.assertEqual(mime, "")
		
		# Verify that subprocess.run was not called
		mock_run.assert_not_called()

	@patch('subprocess.run')
	def test_apply_metadata(self, mock_run):
		"""Test applying metadata to a file"""
		# Create a test file
		test_file = os.path.join(self.test_dir, "test.jpg")
		with open(test_file, 'w') as f:
			f.write("test file content")
		
		# Mock subprocess.run for detect_file_type
		def mock_run_side_effect(*args, **kwargs):
			if '-FileType' in args[0]:
				# This is the detect_file_type call
				mock_process = MagicMock()
				mock_process.returncode = 0
				mock_process.stdout = "JPEG"
				return mock_process
			else:
				# This is the apply_metadata call
				mock_process = MagicMock()
				mock_process.returncode = 0
				return mock_process
		
		mock_run.side_effect = mock_run_side_effect
		
		# Test the method
		metadata_args = ['-DateTimeOriginal=2021:02:03 10:01:18']
		result = ExifToolService.apply_metadata(test_file, metadata_args)
		
		# Verify the result
		self.assertTrue(result)

	@patch('subprocess.run')
	def test_apply_metadata_dry_run(self, mock_run):
		"""Test applying metadata in dry run mode"""
		# Create a test file
		test_file = os.path.join(self.test_dir, "test.jpg")
		with open(test_file, 'w') as f:
			f.write("test file content")
		
		# Mock subprocess.run for detect_file_type
		def mock_run_side_effect(*args, **kwargs):
			if '-FileType' in args[0]:
				# This is the detect_file_type call
				mock_process = MagicMock()
				mock_process.returncode = 0
				mock_process.stdout = "JPEG"
				return mock_process
			else:
				self.fail("subprocess.run should not be called in dry run mode")
		
		mock_run.side_effect = mock_run_side_effect
		
		# Test the method in dry run mode
		metadata_args = ['-DateTimeOriginal=2021:02:03 10:01:18']
		with self.assertLogs(level='INFO') as log:
			result = ExifToolService.apply_metadata(test_file, metadata_args, dry_run=True)
			
			# Verify that the dry run message was logged
			self.assertTrue(any("[DRY RUN]" in entry for entry in log.output))
		
		# Verify the result
		self.assertTrue(result)

	@patch('subprocess.run')
	def test_get_metadata(self, mock_run):
		"""Test getting metadata from a file"""
		# Create a test file
		test_file = os.path.join(self.test_dir, "test.jpg")
		with open(test_file, 'w') as f:
			f.write("test file content")
		
		# Mock subprocess.run to simulate exiftool output
		mock_process = MagicMock()
		mock_process.returncode = 0
		# Note that our implementation expects a list in the JSON output
		mock_process.stdout = '[{"SourceFile":"test.jpg","DateTimeOriginal":"2021:02:03 10:01:18"}]'
		mock_run.return_value = mock_process
		
		# Test the method
		metadata = ExifToolService.get_metadata(test_file)
		
		# Verify the result
		self.assertIsNotNone(metadata, "Metadata should not be None")
		self.assertEqual(metadata.get("SourceFile"), "test.jpg")
		self.assertEqual(metadata.get("DateTimeOriginal"), "2021:02:03 10:01:18")
	
	@patch('subprocess.run')
	def test_get_metadata_empty_result(self, mock_run):
		"""Test getting metadata when exiftool returns empty result"""
		# Create a test file
		test_file = os.path.join(self.test_dir, "empty.jpg")
		with open(test_file, 'w') as f:
			f.write("test file content")
		
		# Mock subprocess.run to simulate exiftool output with empty array
		mock_process = MagicMock()
		mock_process.returncode = 0
		mock_process.stdout = '[]'
		mock_run.return_value = mock_process
		
		# Test the method
		metadata = ExifToolService.get_metadata(test_file)
		
		# Verify the result is an empty dict, not None
		self.assertIsNotNone(metadata)
		self.assertEqual(metadata, {})
	
	@patch('subprocess.run')
	def test_get_metadata_error(self, mock_run):
		"""Test getting metadata when exiftool returns an error"""
		# Create a test file
		test_file = os.path.join(self.test_dir, "error.jpg")
		with open(test_file, 'w') as f:
			f.write("test file content")
		
		# Mock subprocess.run to simulate exiftool error
		mock_process = MagicMock()
		mock_process.returncode = 1
		mock_process.stderr = 'Error reading file'
		mock_run.return_value = mock_process
		
		# Test the method
		metadata = ExifToolService.get_metadata(test_file)
		
		# Verify the result is None when there's an error
		self.assertIsNone(metadata)
	
	@patch('subprocess.run')
	def test_get_metadata_json_error(self, mock_run):
		"""Test getting metadata when exiftool returns invalid JSON"""
		# Create a test file
		test_file = os.path.join(self.test_dir, "invalid_json.jpg")
		with open(test_file, 'w') as f:
			f.write("test file content")
		
		# Mock subprocess.run to simulate exiftool with invalid JSON output
		mock_process = MagicMock()
		mock_process.returncode = 0
		mock_process.stdout = '{invalid json}'
		mock_run.return_value = mock_process
		
		# Test the method
		metadata = ExifToolService.get_metadata(test_file)
		
		# Verify the result is None when there's a JSON error
		self.assertIsNone(metadata)


	@patch('os.path.exists')
	def test_get_metadata_nonexistent_file(self, mock_exists):
		"""Test getting metadata for a file that doesn't exist"""
		# Mock os.path.exists to return False
		mock_exists.return_value = False
		
		# Test the method with a non-existent file
		metadata = ExifToolService.get_metadata("/path/to/nonexistent.jpg")
		
		# Verify the result is None
		self.assertIsNone(metadata)
	
	@patch('subprocess.run')
	def test_specialized_metadata_for_problematic_files(self, mock_run):
		"""Test applying specialized metadata for problematic file types"""
		# Create a test MPG file
		test_file = os.path.join(self.test_dir, "test.mpg")
		with open(test_file, 'w') as f:
			f.write("test mpg content")
		
		# Mock subprocess.run to simulate successful exiftool execution
		mock_process = MagicMock()
		mock_process.returncode = 0
		mock_run.return_value = mock_process
		
		# Test the method
		result = ExifToolService.apply_specialized_metadata_for_problematic_files(test_file)
		
		# Verify the result
		self.assertTrue(result)
		
		# Verify that the command included the special flags for MPG files
		cmd_args = mock_run.call_args[0][0]
		self.assertIn('-P', cmd_args)
		self.assertIn('-F', cmd_args)
	
	@patch('subprocess.run')
	def test_detect_file_type_png(self, mock_run):
		"""Test detecting PNG file type"""
		# Create a test PNG file
		test_file = os.path.join(self.test_dir, "test.png")
		with open(test_file, 'w') as f:
			f.write("test png content")
		
		# Mock subprocess.run to simulate exiftool output for PNG
		# The implementation calls exiftool with -FileType -s3 flags which returns just the file type
		mock_process = MagicMock()
		mock_process.returncode = 0
		mock_process.stdout = "PNG"
		mock_run.return_value = mock_process
		
		# Test the method
		ext, mime = ExifToolService.detect_file_type(test_file)
		
		# Verify the result
		self.assertEqual(ext, "png")
		self.assertTrue(mime.startswith("image/png") or mime == "")


	@patch('subprocess.run')
	def test_specialized_metadata_error(self, mock_run):
		"""Test error handling in specialized metadata application"""
		# Create a test file
		test_file = os.path.join(self.test_dir, "test.avi")
		with open(test_file, 'w') as f:
			f.write("test avi content")
		
		# Mock subprocess.run to simulate an error
		mock_process = MagicMock()
		mock_process.returncode = 1
		mock_process.stderr = "Error processing file"
		mock_run.return_value = mock_process
		
		# Test the method
		result = ExifToolService.apply_specialized_metadata_for_problematic_files(test_file)
		
		# Verify the result
		self.assertFalse(result)
	
	@patch('subprocess.run')
	def test_apply_metadata_command_timeout(self, mock_run):
		"""Test handling of command timeout in apply_metadata"""
		# Create a test file
		test_file = os.path.join(self.test_dir, "timeout.jpg")
		with open(test_file, 'w') as f:
			f.write("test content")
		
		# Mock subprocess.run to simulate a timeout
		mock_run.side_effect = subprocess.TimeoutExpired(cmd="exiftool", timeout=15)
		
		# Test the method
		result = ExifToolService.apply_metadata(test_file, ["-Title=Test"])
		
		# Verify the result
		self.assertFalse(result)
	
	@patch('subprocess.run')
	def test_detect_file_type_fallback(self, mock_run):
		"""Test fallback mechanism in file type detection"""
		# Create a test file with unusual extension
		test_file = os.path.join(self.test_dir, "test.xyz")
		with open(test_file, 'w') as f:
			f.write("test content")
		
		# Mock first subprocess.run call to fail
		first_result = MagicMock()
		first_result.returncode = 1
		
		# Mock second subprocess.run call to succeed with file command
		second_result = MagicMock()
		second_result.returncode = 0
		second_result.stdout = "image/jpeg"
		
		# Configure mock to return different results on successive calls
		mock_run.side_effect = [first_result, second_result]
		
		# Test the method
		ext, mime = ExifToolService.detect_file_type(test_file)
		
		# Verify the result shows fallback to file command worked
		self.assertEqual(ext, "jpg")
		self.assertEqual(mime, "image/jpeg")


if __name__ == "__main__":
	unittest.main()
