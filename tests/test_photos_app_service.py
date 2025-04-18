#!/usr/bin/env python3
"""
Unit tests for photos_app_service module
"""
import os
import sys
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.photos_app_service import PhotosAppService


class TestPhotosAppService(unittest.TestCase):
	"""Test cases for PhotosAppService class"""

	def setUp(self):
		"""Set up test environment"""
		# Create a temporary directory for test files
		self.temp_dir = tempfile.TemporaryDirectory()
		self.test_dir = self.temp_dir.name

	def tearDown(self):
		"""Clean up test environment"""
		self.temp_dir.cleanup()

	def test_get_photo_timestamp_from_json_file(self):
		"""Test extracting timestamp from a JSON metadata file"""
		# Create a test JSON file
		test_json = {
			"title": "Test Photo",
			"photoTakenTime": {
				"timestamp": "1612345678"
			}
		}
		json_path = os.path.join(self.test_dir, "test_photo.json")
		with open(json_path, 'w') as f:
			json.dump(test_json, f)

		# Test the method
		timestamp = PhotosAppService.get_photo_timestamp(json_path)
		self.assertEqual(timestamp, "1612345678")

	def test_get_photo_timestamp_from_photo_path(self):
		"""Test extracting timestamp from a photo path (JSON file is created automatically)"""
		# Create a test JSON file
		test_json = {
			"title": "Test Photo",
			"photoTakenTime": {
				"timestamp": "1612345678"
			}
		}
		photo_path = os.path.join(self.test_dir, "test_photo.jpg")
		json_path = photo_path + ".json"
		with open(json_path, 'w') as f:
			json.dump(test_json, f)

		# Test the method
		timestamp = PhotosAppService.get_photo_timestamp(photo_path)
		self.assertEqual(timestamp, "1612345678")

	def test_get_photo_timestamp_missing_json(self):
		"""Test extracting timestamp when JSON file doesn't exist"""
		photo_path = os.path.join(self.test_dir, "nonexistent_photo.jpg")
		timestamp = PhotosAppService.get_photo_timestamp(photo_path)
		self.assertEqual(timestamp, "")

	def test_get_photo_timestamp_invalid_json(self):
		"""Test extracting timestamp from an invalid JSON file"""
		# Create an invalid JSON file
		json_path = os.path.join(self.test_dir, "invalid.json")
		with open(json_path, 'w') as f:
			f.write("This is not valid JSON")

		# Test the method
		timestamp = PhotosAppService.get_photo_timestamp(json_path)
		self.assertEqual(timestamp, "")

	def test_get_photo_timestamp_missing_timestamp(self):
		"""Test extracting timestamp when timestamp field is missing"""
		# Create a test JSON file without timestamp
		test_json = {
			"title": "Test Photo"
			# No photoTakenTime field
		}
		json_path = os.path.join(self.test_dir, "no_timestamp.json")
		with open(json_path, 'w') as f:
			json.dump(test_json, f)

		# Test the method
		timestamp = PhotosAppService.get_photo_timestamp(json_path)
		self.assertEqual(timestamp, "")

	@patch('subprocess.Popen')
	def test_run_applescript(self, mock_popen):
		"""Test the _run_applescript method"""
		# Mock the subprocess.Popen
		process_mock = MagicMock()
		process_mock.communicate.return_value = (b"test_output", b"")
		mock_popen.return_value = process_mock

		# Test the method
		result = PhotosAppService._run_applescript("test_script", ["arg1", "arg2"], "Test Error")
		
		# Verify the result
		self.assertEqual(result, "test_output")
		
		# Verify that Popen was called correctly
		mock_popen.assert_called_once_with(
			["osascript", "-", "arg1", "arg2"],
			stdin=unittest.mock.ANY,
			stdout=unittest.mock.ANY,
			stderr=unittest.mock.ANY
		)

	@patch('subprocess.Popen')
	def test_run_applescript_with_error(self, mock_popen):
		"""Test the _run_applescript method when an error occurs"""
		# Mock the subprocess.Popen
		process_mock = MagicMock()
		process_mock.communicate.return_value = (b"", b"test_error")
		mock_popen.return_value = process_mock

		# Test the method
		with self.assertLogs(level='ERROR') as log:
			result = PhotosAppService._run_applescript("test_script", ["arg1", "arg2"], "Test Error")
			
			# Verify that the error was logged
			self.assertIn("Test Error: test_error", log.output[0])
		
		# Verify the result
		self.assertEqual(result, "")

	def test_load_save_progress(self):
		"""Test loading and saving progress"""
		# Set up a test progress file path
		test_progress_file = os.path.join(self.test_dir, "test_progress.json")
		
		# Save the original progress file path
		original_progress_file = PhotosAppService.PROGRESS_FILE
		
		try:
			# Set the progress file to our test file
			PhotosAppService.PROGRESS_FILE = test_progress_file
			
			# Test saving progress
			test_progress = {"album1": True, "album2": False}
			PhotosAppService.save_progress(test_progress)
			
			# Verify that the file was created
			self.assertTrue(os.path.exists(test_progress_file))
			
			# Test loading progress
			loaded_progress = PhotosAppService.load_progress()
			
			# Verify the loaded progress
			self.assertEqual(loaded_progress, test_progress)
			
		finally:
			# Restore the original progress file path
			PhotosAppService.PROGRESS_FILE = original_progress_file


	@patch('subprocess.Popen')
	def test_import_photo(self, mock_popen):
		"""Test importing a photo to Apple Photos"""
		# Mock subprocess.Popen
		mock_process = MagicMock()
		mock_process.communicate.return_value = (b"", b"")
		mock_process.returncode = 0
		mock_popen.return_value = mock_process
		
		# Create a test photo file
		photo_path = os.path.join(self.test_dir, "test_photo.jpg")
		with open(photo_path, 'wb') as f:
			f.write(b"test photo content")
		
		# Test the method
		result = PhotosAppService.import_photo(photo_path, "1612345678")
		self.assertTrue(result)
		
		# Verify that subprocess.Popen was called
		mock_popen.assert_called_once()

	@patch('subprocess.Popen')
	def test_import_photo_error(self, mock_popen):
		"""Test importing a photo when an error occurs"""
		# Mock subprocess.Popen to return an error
		mock_process = MagicMock()
		mock_process.communicate.return_value = (b"", b"Error importing photo")
		mock_process.returncode = 1
		mock_popen.return_value = mock_process
		
		# Create a test photo file
		photo_path = os.path.join(self.test_dir, "test_photo.jpg")
		with open(photo_path, 'wb') as f:
			f.write(b"test photo content")
		
		# Test the method
		result = PhotosAppService.import_photo(photo_path, "1612345678")
		self.assertFalse(result)

	@patch('os.path.exists')
	def test_import_photo_nonexistent_file(self, mock_exists):
		"""Test importing a photo that doesn't exist"""
		# Mock os.path.exists to return False
		mock_exists.return_value = False
		
		# Test the method
		result = PhotosAppService.import_photo("/path/to/nonexistent.jpg", "1612345678")
		self.assertFalse(result)

	@patch('subprocess.Popen')
	def test_batch_import_photos(self, mock_popen):
		"""Test batch importing photos to Apple Photos"""
		# Mock subprocess.Popen
		mock_process = MagicMock()
		mock_process.communicate.return_value = (b"", b"")
		mock_process.returncode = 0
		mock_popen.return_value = mock_process
		
		# Create test photo files
		photo_paths = []
		for i in range(3):
			photo_path = os.path.join(self.test_dir, f"test_photo_{i}.jpg")
			with open(photo_path, 'wb') as f:
				f.write(b"test photo content")
			photo_paths.append(photo_path)
		
		# Test the method
		results = PhotosAppService.batch_import_photos(photo_paths)
		self.assertEqual(len(results), 3)
		self.assertTrue(all(results))
		
		# Verify that subprocess.Popen was called for each photo
		self.assertEqual(mock_popen.call_count, 3)

	@patch('os.path.exists')
	def test_save_progress(self, mock_exists):
		"""Test saving progress to a file"""
		# Mock os.path.exists to return True for the directory
		mock_exists.return_value = True
		
		# Create test data
		progress_data = {
			"processed_files": ["file1.jpg", "file2.jpg"],
			"total_files": 10,
			"current_index": 2
		}
		
		# Create a progress file path
		progress_file = os.path.join(self.test_dir, "progress.json")
		
		# Test the method
		with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
			result = PhotosAppService.save_progress(progress_data, progress_file)
			self.assertTrue(result)
			
			# Verify that the file was opened for writing
			mock_file.assert_called_once_with(progress_file, 'w')

	@patch('os.path.exists')
	def test_load_progress(self, mock_exists):
		"""Test loading progress from a file"""
		# Create test progress data
		progress_data = {
			"processed_files": ["file1.jpg", "file2.jpg"],
			"total_files": 10,
			"current_index": 2
		}
		
		# Create a progress file
		progress_file = os.path.join(self.test_dir, "progress.json")
		with open(progress_file, 'w') as f:
			json.dump(progress_data, f)
		
		# Mock os.path.exists to return True
		mock_exists.return_value = True
		
		# Test the method
		loaded_data = PhotosAppService.load_progress(progress_file)
		self.assertEqual(loaded_data, progress_data)

	@patch('os.path.exists')
	def test_load_progress_nonexistent_file(self, mock_exists):
		"""Test loading progress from a nonexistent file"""
		# Mock os.path.exists to return False
		mock_exists.return_value = False
		
		# Test the method
		loaded_data = PhotosAppService.load_progress("/path/to/nonexistent.json")
		self.assertEqual(loaded_data, {})

	@patch('os.path.exists')
	def test_load_progress_invalid_json(self, mock_exists):
		"""Test loading progress from an invalid JSON file"""
		# Create an invalid JSON file
		progress_file = os.path.join(self.test_dir, "invalid.json")
		with open(progress_file, 'w') as f:
			f.write("This is not valid JSON")
		
		# Mock os.path.exists to return True
		mock_exists.return_value = True
		
		# Test the method
		loaded_data = PhotosAppService.load_progress(progress_file)
		self.assertEqual(loaded_data, {})

if __name__ == "__main__":
	unittest.main()
