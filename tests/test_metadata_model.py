#!/usr/bin/env python3
"""
Tests for the metadata model classes
"""
import unittest
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.metadata import Metadata, PhotoMetadata


class TestMetadata(unittest.TestCase):
    """Test the Metadata class"""

    def test_init(self):
        """Test initialization of Metadata class"""
        metadata = Metadata(
            title="Test Title",
            date_taken="2023:01:01 12:00:00",
            latitude=37.7749,
            longitude=-122.4194
        )

        self.assertEqual(metadata.title, "Test Title")
        self.assertEqual(metadata.date_taken, "2023:01:01 12:00:00")
        self.assertEqual(metadata.latitude, 37.7749)
        self.assertEqual(metadata.longitude, -122.4194)

    def test_to_exiftool_args(self):
        """Test conversion to exiftool arguments"""
        metadata = Metadata(
            title="Test Title",
            date_taken="2023:01:01 12:00:00",
            latitude=37.7749,
            longitude=-122.4194
        )

        args = metadata.to_exiftool_args()

        self.assertIn("-Title=Test Title", args)
        self.assertIn("-DateTimeOriginal=2023:01:01 12:00:00", args)
        self.assertIn("-CreateDate=2023:01:01 12:00:00", args)
        self.assertIn("-ModifyDate=2023:01:01 12:00:00", args)
        self.assertIn("-GPSLatitude=37.7749", args)
        self.assertIn("-GPSLongitude=-122.4194", args)
        self.assertIn("-GPSLatitudeRef=N", args)
        self.assertIn("-GPSLongitudeRef=W", args)

    def test_to_exiftool_args_partial(self):
        """Test conversion to exiftool arguments with partial data"""
        # Test with only title
        metadata1 = Metadata(title="Test Title")
        args1 = metadata1.to_exiftool_args()
        self.assertIn("-Title=Test Title", args1)
        self.assertEqual(len(args1), 1)

        # Test with only date
        metadata2 = Metadata(date_taken="2023:01:01 12:00:00")
        args2 = metadata2.to_exiftool_args()
        self.assertIn("-DateTimeOriginal=2023:01:01 12:00:00", args2)
        self.assertIn("-CreateDate=2023:01:01 12:00:00", args2)
        self.assertIn("-ModifyDate=2023:01:01 12:00:00", args2)
        self.assertEqual(len(args2), 3)

        # Test with only coordinates
        metadata3 = Metadata(latitude=37.7749, longitude=-122.4194)
        args3 = metadata3.to_exiftool_args()
        self.assertIn("-GPSLatitude=37.7749", args3)
        self.assertIn("-GPSLongitude=-122.4194", args3)
        self.assertIn("-GPSLatitudeRef=N", args3)
        self.assertIn("-GPSLongitudeRef=W", args3)
        self.assertEqual(len(args3), 4)


class TestPhotoMetadata(unittest.TestCase):
    """Test the PhotoMetadata class"""

    def setUp(self):
        """Set up test data"""
        self.test_data_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "test_data"
        os.makedirs(self.test_data_dir, exist_ok=True)

        # Create a sample JSON file
        self.sample_json = {
            "title": "IMG_1234.jpg",
            "photoTakenTime": {
                "timestamp": "1609459200"  # 2021-01-01 00:00:00
            },
            "description": "Test description",
            "geoData": {
                "latitude": 37.7749,
                "longitude": -122.4194
            }
        }

        self.json_path = self.test_data_dir / "sample.json"
        with open(self.json_path, "w") as f:
            json.dump(self.sample_json, f)

    def tearDown(self):
        """Clean up test data"""
        if os.path.exists(self.json_path):
            os.remove(self.json_path)

    def test_from_json(self):
        """Test creation from JSON data"""
        metadata = PhotoMetadata.from_json(self.sample_json)

        self.assertEqual(metadata.filename, "IMG_1234.jpg")
        # Check that the timestamp was converted to a datetime (exact time may vary by timezone)
        self.assertEqual(metadata.date_taken.timestamp(), int(self.sample_json["photoTakenTime"]["timestamp"]))
        self.assertEqual(metadata.title, "IMG_1234.jpg")
        self.assertEqual(metadata.description, "Test description")
        self.assertEqual(metadata.latitude, 37.7749)
        self.assertEqual(metadata.longitude, -122.4194)
        self.assertEqual(metadata.raw_data, self.sample_json)

    def test_from_json_missing_fields(self):
        """Test creation from JSON data with missing fields"""
        # Test with missing photoTakenTime but with creationTime
        json_data = {
            "title": "IMG_1234.jpg",
            "creationTime": {
                "timestamp": "1609459200"  # 2021-01-01 00:00:00
            }
        }

        metadata = PhotoMetadata.from_json(json_data)
        self.assertEqual(metadata.filename, "IMG_1234.jpg")
        # Check that the timestamp was converted to a datetime (exact time may vary by timezone)
        self.assertEqual(metadata.date_taken.timestamp(), int(json_data["creationTime"]["timestamp"]))
        self.assertIsNone(metadata.latitude)
        self.assertIsNone(metadata.longitude)

        # Test with missing both photoTakenTime and creationTime
        json_data = {
            "title": "IMG_1234.jpg"
        }

        metadata = PhotoMetadata.from_json(json_data)
        self.assertEqual(metadata.filename, "IMG_1234.jpg")
        # Should use current time as fallback, so just check it's a datetime
        self.assertIsInstance(metadata.date_taken, datetime)

    def test_to_exiftool_args(self):
        """Test conversion to exiftool arguments"""
        metadata = PhotoMetadata.from_json(self.sample_json)
        args = metadata.to_exiftool_args()

        date_str = metadata.date_taken.strftime('%Y:%m:%d %H:%M:%S')

        self.assertIn(f"-DateTimeOriginal={date_str}", args)
        self.assertIn(f"-CreateDate={date_str}", args)
        self.assertIn(f"-ModifyDate={date_str}", args)
        self.assertIn("-Title=IMG_1234.jpg", args)
        self.assertIn("-Description=Test description", args)
        self.assertIn("-ImageDescription=Test description", args)
        self.assertIn("-GPSLatitude=37.7749", args)
        self.assertIn("-GPSLongitude=-122.4194", args)

    def test_to_exiftool_args_partial(self):
        """Test conversion to exiftool arguments with partial data"""
        # Test with minimal data
        json_data = {
            "title": "IMG_1234.jpg",
            "photoTakenTime": {
                "timestamp": "1609459200"  # 2021-01-01 00:00:00
            }
        }

        metadata = PhotoMetadata.from_json(json_data)
        args = metadata.to_exiftool_args()

        date_str = metadata.date_taken.strftime('%Y:%m:%d %H:%M:%S')

        self.assertIn(f"-DateTimeOriginal={date_str}", args)
        self.assertIn(f"-CreateDate={date_str}", args)
        self.assertIn(f"-ModifyDate={date_str}", args)
        self.assertIn("-Title=IMG_1234.jpg", args)

        # These should not be in the args
        self.assertNotIn("-Description=", " ".join(args))
        self.assertNotIn("-ImageDescription=", " ".join(args))
        self.assertNotIn("-GPSLatitude=", " ".join(args))
        self.assertNotIn("-GPSLongitude=", " ".join(args))


if __name__ == "__main__":
    unittest.main()
