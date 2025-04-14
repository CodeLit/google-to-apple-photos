"""
Utility functions for file operations
"""
import os
import re
from pathlib import Path
from typing import Optional, List, Tuple


def get_base_filename(file_path: str) -> str:
	"""
	Extract base filename without extension from a file path.
	Handles special cases in Google Takeout naming.
	
	Args:
		file_path: Path to the file
		
	Returns:
		Base filename without extension
	"""
	filename = os.path.basename(file_path)
	
	# Handle edited files (filename(1).jpg)
	edited_match = re.match(r'(.+)(\(\d+\))(\..+)', filename)
	if edited_match:
		return edited_match.group(1)
	
	# Regular case
	return os.path.splitext(filename)[0]


def find_matching_file(base_name: str, target_dir: str) -> Optional[str]:
	"""
	Find a file in target_dir that matches the base_name.
	
	Args:
		base_name: Base filename to match
		target_dir: Directory to search in
		
	Returns:
		Path to the matching file or None if not found
	"""
	# First try exact match
	for ext in ['.jpg', '.jpeg', '.png', '.mp4', '.mov', '.heic', '.gif']:
		exact_match = os.path.join(target_dir, f"{base_name}{ext}")
		if os.path.exists(exact_match):
			return exact_match
	
	# Try case-insensitive match
	for file in os.listdir(target_dir):
		file_base = get_base_filename(file)
		if file_base.lower() == base_name.lower():
			return os.path.join(target_dir, file)
	
	return None


def find_json_media_pairs(source_dir: str) -> List[Tuple[str, str]]:
	"""
	Find pairs of JSON metadata files and their corresponding media files
	
	Args:
		source_dir: Directory to search in
		
	Returns:
		List of tuples (json_file, media_file)
	"""
	pairs = []
	
	for root, _, files in os.walk(source_dir):
		for file in files:
			if file.endswith('.json'):
				# Check if this is a metadata file
				if '.supplemental-metadata' in file or '.supplemental-meta' in file:
					# Get the base filename
					media_filename = file.replace('.supplemental-metadata.json', '')
					media_filename = media_filename.replace('.supplemental-meta.json', '')
					
					# Find the corresponding media file
					media_path = os.path.join(root, media_filename)
					if os.path.exists(media_path):
						pairs.append((os.path.join(root, file), media_path))
	
	return pairs
