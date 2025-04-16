#!/usr/bin/env python3
"""
Unit tests for file_utils module
"""
import os
import sys
import unittest
from pathlib import Path

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.file_utils import extract_date_from_filename, is_uuid_filename, are_duplicate_filenames


class TestFileUtils(unittest.TestCase):
	"""Test cases for file_utils module"""

	def test_extract_date_from_google_takeout_pattern(self):
		"""Test extracting date from Google Takeout pattern"""
		# Test basic pattern
		result = extract_date_from_filename("IMG20230608154246.jpg")
		self.assertIsNotNone(result)
		date_str, pattern_desc = result
		self.assertEqual(date_str, "2023:06:08")
		self.assertEqual(pattern_desc, "Google Takeout pattern")

		# Test with sequence number
		result = extract_date_from_filename("IMG20210503102004_06.jpg")
		self.assertIsNotNone(result)
		date_str, pattern_desc = result
		self.assertEqual(date_str, "2021:05:03")
		self.assertEqual(pattern_desc, "Google Takeout pattern")

		# Test video pattern
		result = extract_date_from_filename("VID20210416150540.mp4")
		self.assertIsNotNone(result)
		date_str, pattern_desc = result
		self.assertEqual(date_str, "2021:04:16")
		self.assertEqual(pattern_desc, "Google Takeout pattern")

	def test_extract_date_from_whatsapp_pattern(self):
		"""Test extracting date from WhatsApp pattern"""
		result = extract_date_from_filename("IMG-20210307-WA0001.jpg")
		self.assertIsNotNone(result)
		date_str, pattern_desc = result
		self.assertEqual(date_str, "2021:03:07")
		self.assertIn("IMG-YYYYMMDD pattern", pattern_desc)

		# Test video pattern
		result = extract_date_from_filename("VID-20210307-WA0001.jpg")
		self.assertIsNotNone(result)
		date_str, pattern_desc = result
		self.assertEqual(date_str, "2021:03:07")
		self.assertIn("WhatsApp pattern", pattern_desc)

	def test_extract_date_from_formatted_date_pattern(self):
		"""Test extracting date from formatted date patterns"""
		# Test YYYY-MM-DD_HH-MM-SS pattern
		result = extract_date_from_filename("2021-03-07_23-15-52.jpg")
		self.assertIsNotNone(result)
		date_str, pattern_desc = result
		self.assertEqual(date_str, "2021:03:07")
		self.assertEqual(pattern_desc, "YYYY-MM-DD_HH-MM-SS pattern")

		# Test YYYYMMDD_HHMMSS pattern
		result = extract_date_from_filename("20210307_231552.jpg")
		self.assertIsNotNone(result)
		date_str, pattern_desc = result
		self.assertEqual(date_str, "2021:03:07")
		self.assertEqual(pattern_desc, "YYYYMMDD_HHMMSS pattern")

	def test_extract_date_from_screenshot_pattern(self):
		"""Test extracting date from screenshot pattern"""
		result = extract_date_from_filename("Screenshot_20210307-231552.jpg")
		self.assertIsNotNone(result)
		date_str, pattern_desc = result
		self.assertEqual(date_str, "2021:03:07")
		self.assertEqual(pattern_desc, "Screenshot pattern")

	def test_no_date_in_filename(self):
		"""Test files with no date in the filename"""
		# Standard Apple pattern
		result = extract_date_from_filename("IMG_1234.jpg")
		self.assertIsNone(result)

		# Descriptive name
		result = extract_date_from_filename("День рождения 001.JPG")
		self.assertIsNone(result)

	def test_invalid_dates(self):
		"""Test files with invalid dates in the filename"""
		# Invalid month
		result = extract_date_from_filename("IMG-20211307-WA0001.jpg")
		self.assertIsNone(result)

		# Invalid day
		result = extract_date_from_filename("IMG-20210232-WA0001.jpg")
		self.assertIsNone(result)

	def test_uuid_filename_detection(self):
		"""Test detection of UUID-style filenames"""
		# Valid UUID filenames
		self.assertTrue(is_uuid_filename("1D259D70-974B-4D1C-921E-7F35783509C1_1_201_a.jpeg"))
		self.assertTrue(is_uuid_filename("1D259D70-974B-4D1C-921E-7F35783509C1.jpg"))
		self.assertTrue(is_uuid_filename("1D259D70-974B-4D1C-921E-7F35783509C1_1.heic"))
		self.assertTrue(is_uuid_filename("1D259D70-974B-4D1C-921E-7F35783509C1_1_201.png"))

		# Invalid UUID filenames
		self.assertFalse(is_uuid_filename("IMG_1234.jpg"))
		self.assertFalse(is_uuid_filename("IMG20230608154246.jpg"))
		self.assertFalse(is_uuid_filename("2021-03-07_23-15-52.jpg"))

	def test_duplicate_filename_detection(self):
		"""Test detection of duplicate filenames"""
		# Same UUID with different extensions
		self.assertTrue(are_duplicate_filenames(
			"1D259D70-974B-4D1C-921E-7F35783509C1_1_201_a.jpeg",
			"1D259D70-974B-4D1C-921E-7F35783509C1_1_201_a.jpg"
		))

		# Same UUID with different modifiers
		self.assertTrue(are_duplicate_filenames(
			"1D259D70-974B-4D1C-921E-7F35783509C1_1_201_a.jpeg",
			"1D259D70-974B-4D1C-921E-7F35783509C1.jpg"
		))

		# Same base name with different extensions
		self.assertTrue(are_duplicate_filenames("IMG_1234.jpg", "IMG_1234.jpeg"))
		self.assertTrue(are_duplicate_filenames("IMG_1234.jpg", "IMG_1234.heic"))

		# Different filenames
		self.assertFalse(are_duplicate_filenames("IMG_1234.jpg", "IMG_5678.jpg"))
		self.assertFalse(are_duplicate_filenames(
			"1D259D70-974B-4D1C-921E-7F35783509C1.jpg",
			"2E369E81-085C-4E2D-932F-8F46794E621D.jpg"
		))


if __name__ == "__main__":
	unittest.main()
