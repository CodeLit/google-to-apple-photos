#!/usr/bin/env python3
"""
Google Photos to Apple Photos Metadata Synchronizer

This script synchronizes metadata (especially dates) from Google Takeout JSON files
to corresponding media files exported from Apple Photos, allowing for correct
metadata when reimporting into Apple Photos.
"""

import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main function from the src module
from src.main import main


if __name__ == '__main__':
	sys.exit(main())
