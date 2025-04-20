import os
import shutil
import unittest
import tempfile
import logging
import hashlib
from pathlib import Path

from src.services.exiftool_service import ExifToolService
from src.utils.image_utils import compute_file_hash

logger = logging.getLogger(__name__)

class TestFileExtensionFix(unittest.TestCase):
	"""Test the file extension fix functionality"""
	
	def setUp(self):
		"""Set up the test environment"""
		# Create a temporary directory for testing
		self.test_dir = tempfile.mkdtemp()
		
		# Create test files with incorrect extensions
		self.jpg_as_heic = os.path.join(self.test_dir, "test_jpg_as_heic.heic")
		self.heic_as_jpg = os.path.join(self.test_dir, "test_heic_as_jpg.jpg")
		self.mp4_as_mov = os.path.join(self.test_dir, "test_mp4_as_mov.mov")
		
		# Create a JPEG file with .heic extension
		with open(self.jpg_as_heic, 'wb') as f:
			# Write JPEG file signature and minimal header
			f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00')
			# Add some dummy image data
			f.write(b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01')
			f.write(b'\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00')
			f.write(b'\x00\x00\x00\x00\xff\xd9')
		
		# Create a HEIC-like file with .jpg extension
		with open(self.heic_as_jpg, 'wb') as f:
			# Write HEIC file signature
			f.write(b'\x00\x00\x00\x20ftypheic\x00\x00\x00\x00heic\x00\x00\x00\x00')
			# Add some dummy container data
			f.write(b'\x00\x00\x00\x10meta\x00\x00\x00\x00')
		
		# Create an MP4 file with .mov extension
		with open(self.mp4_as_mov, 'wb') as f:
			# Write MP4 file signature
			f.write(b'\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00')
			# Add some dummy container data
			f.write(b'\x00\x00\x00\x08free\x00\x00\x00\x00')
	
	def tearDown(self):
		"""Clean up after the test"""
		# Remove the temporary directory and its contents
		shutil.rmtree(self.test_dir)
	
	def test_fix_jpg_with_heic_extension(self):
		"""Test fixing a JPG file with a HEIC extension"""
		# Ensure the original file exists
		self.assertTrue(os.path.exists(self.jpg_as_heic))
		
		# Fix the file extension
		fixed_path = ExifToolService.fix_file_extension(self.jpg_as_heic)
		
		# Check that the fixed path is different from the original
		self.assertNotEqual(fixed_path, self.jpg_as_heic)
		
		# Check that the fixed file exists
		self.assertTrue(os.path.exists(fixed_path))
		
		# Check that the original file no longer exists
		self.assertFalse(os.path.exists(self.jpg_as_heic))
		
		# Check that the fixed file has the correct extension
		self.assertTrue(fixed_path.lower().endswith('.jpg'))
	
	def test_fix_heic_with_jpg_extension(self):
		"""Test fixing a HEIC file with a JPG extension"""
		# Ensure the original file exists
		self.assertTrue(os.path.exists(self.heic_as_jpg))
		
		# Fix the file extension
		fixed_path = ExifToolService.fix_file_extension(self.heic_as_jpg)
		
		# Check that the fixed path is different from the original
		self.assertNotEqual(fixed_path, self.heic_as_jpg)
		
		# Check that the fixed file exists
		self.assertTrue(os.path.exists(fixed_path))
		
		# Check that the original file no longer exists
		self.assertFalse(os.path.exists(self.heic_as_jpg))
		
		# Check that the fixed file has the correct extension
		self.assertTrue(fixed_path.lower().endswith('.heic'))
	
	def test_fix_mp4_with_mov_extension(self):
		"""Test fixing an MP4 file with a MOV extension"""
		# Ensure the original file exists
		self.assertTrue(os.path.exists(self.mp4_as_mov))
		
		# Fix the file extension
		fixed_path = ExifToolService.fix_file_extension(self.mp4_as_mov)
		
		# Check that the fixed path is different from the original
		self.assertNotEqual(fixed_path, self.mp4_as_mov)
		
		# Check that the fixed file exists
		self.assertTrue(os.path.exists(fixed_path))
		
		# Check that the original file no longer exists
		self.assertFalse(os.path.exists(self.mp4_as_mov))
		
		# Check that the fixed file has the correct extension
		self.assertTrue(fixed_path.lower().endswith('.mp4'))

if __name__ == '__main__':
	unittest.main()
