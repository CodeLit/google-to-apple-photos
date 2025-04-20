import os
import shutil
import unittest
import tempfile
import logging
from pathlib import Path

from src.utils.image_utils import find_duplicates, compute_file_hash
from src.services.metadata_service import MetadataService

logger = logging.getLogger(__name__)

class TestDuplicateFiles(unittest.TestCase):
	"""Test the duplicate file detection and handling functionality"""
	
	def setUp(self):
		"""Set up the test environment"""
		# Create a temporary directory for testing
		self.test_dir = tempfile.mkdtemp()
		
		# Create test files with duplicate content but different names
		self.original_jpg = os.path.join(self.test_dir, "IMG_3132.jpg")
		self.duplicate_jpg = os.path.join(self.test_dir, "IMG_3132 (1).jpg")
		self.different_jpg = os.path.join(self.test_dir, "IMG_3133.jpg")
		
		# Create sample files for testing
		# Create a JPEG file
		with open(self.original_jpg, 'wb') as f:
			# Write JPEG file signature and minimal header
			f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00')
			# Add some dummy image data
			f.write(b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01')
			f.write(b'\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00')
			f.write(b'\x00\x00\x00\x00\xff\xd9')
		
		# Create a duplicate JPEG file with different name
		shutil.copy2(self.original_jpg, self.duplicate_jpg)
		
		# Create a different JPEG file
		with open(self.different_jpg, 'wb') as f:
			# Write JPEG file signature and minimal header
			f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00')
			# Add some different dummy image data
			f.write(b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01')
			f.write(b'\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00')
			f.write(b'\x01\x01\x01\x01\xff\xd9')
	
	def tearDown(self):
		"""Clean up after the test"""
		# Remove the temporary directory and its contents
		shutil.rmtree(self.test_dir)
	
	def test_duplicate_detection(self):
		"""Test that duplicate files are correctly detected"""
		# Find duplicates in the test directory
		duplicates = find_duplicates(self.test_dir)
		
		# Check that we found the duplicate
		self.assertEqual(len(duplicates), 1, "Should find one group of duplicates")
		
		# Get the original file and its duplicates
		original = list(duplicates.keys())[0]
		duplicate_files = duplicates[original]
		
		# Check that the duplicate was correctly identified
		self.assertEqual(len(duplicate_files), 1, "Should find one duplicate file")
		
		# The original should be the older file (in this case, self.original_jpg)
		# and the duplicate should be self.duplicate_jpg
		self.assertIn(os.path.basename(self.duplicate_jpg), 
					  [os.path.basename(f) for f in duplicate_files],
					  "Duplicate file should be in the list of duplicates")
	
	def test_file_hash_comparison(self):
		"""Test that file hash comparison correctly identifies identical files"""
		# Compute hashes for both files
		original_hash = compute_file_hash(self.original_jpg)
		duplicate_hash = compute_file_hash(self.duplicate_jpg)
		different_hash = compute_file_hash(self.different_jpg)
		
		# Check that the hashes of identical files match
		self.assertEqual(original_hash, duplicate_hash, 
						"Hashes of identical files should match")
		
		# Check that the hashes of different files don't match
		self.assertNotEqual(original_hash, different_hash, 
						  "Hashes of different files should not match")

if __name__ == '__main__':
	unittest.main()
