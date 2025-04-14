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
	# Handle common prefixes in Google Takeout filenames
	prefixes_to_remove = ['IMG_', 'VID_', 'image_', 'video_']
	for prefix in prefixes_to_remove:
		if base_name.startswith(prefix):
			base_name_no_prefix = base_name[len(prefix):]
			# Try matching without prefix first
			result = _try_find_match(base_name_no_prefix, target_dir)
			if result:
				return result
			# If no match, continue with original name
			break
	
	# Try with original name
	return _try_find_match(base_name, target_dir)


def _try_find_match(base_name: str, target_dir: str) -> Optional[str]:
	"""
	Helper function to try different matching strategies for a filename.
	"""
	# Clean the base name for better matching
	clean_base_name = re.sub(r'[^a-zA-Z0-9]', '', base_name.lower())
	
	# Skip very short base names (likely to cause false matches)
	if len(clean_base_name) < 3:
		return None
	
	# First try exact match with various extensions
	for ext in ['.jpg', '.jpeg', '.png', '.mp4', '.mov', '.heic', '.gif', '.JPG', '.JPEG', '.PNG', '.MP4', '.MOV', '.HEIC', '.GIF']:
		exact_match = os.path.join(target_dir, f"{base_name}{ext}")
		if os.path.exists(exact_match):
			return exact_match
	
	# Try with Apple's modified filename patterns (IMG_E1234.jpg for edited photos)
	if not base_name.startswith('IMG_E') and not base_name.startswith('VID_E'):
		for prefix in ['IMG_E', 'VID_E']:
			for ext in ['.jpg', '.jpeg', '.png', '.mp4', '.mov', '.heic', '.gif']:
				apple_match = os.path.join(target_dir, f"{prefix}{base_name[4:]}{ext}" if base_name.startswith(('IMG_', 'VID_')) else f"{prefix}{base_name}{ext}")
				if os.path.exists(apple_match):
					return apple_match
	
	# Get list of files in target directory
	target_files = []
	try:
		target_files = os.listdir(target_dir)
	except (PermissionError, FileNotFoundError) as e:
		print(f"Error accessing directory {target_dir}: {e}")
		return None
	
	# First pass: exact base name match (case insensitive)
	for file in target_files:
		file_base = get_base_filename(file)
		if file_base.lower() == base_name.lower():
			return os.path.join(target_dir, file)
	
	# Second pass: check if base name is contained in the filename
	for file in target_files:
		file_base = get_base_filename(file)
		
		# Skip very short file names
		if len(file_base) < 3:
			continue
		
		# Check for exact containment
		if base_name.lower() in file_base.lower() or file_base.lower() in base_name.lower():
			return os.path.join(target_dir, file)
	
	# Third pass: use more aggressive cleaning and matching
	for file in target_files:
		file_base = get_base_filename(file)
		clean_file_base = re.sub(r'[^a-zA-Z0-9]', '', file_base.lower())
		
		# Skip very short file names
		if len(clean_file_base) < 3:
			continue
		
		# Check for substantial overlap
		if clean_file_base in clean_base_name or clean_base_name in clean_file_base:
			return os.path.join(target_dir, file)
		
		# Check for numeric sequence match (e.g., IMG_1234 matching with 1234)
		num_match_base = re.search(r'\d{4,}', base_name)
		num_match_file = re.search(r'\d{4,}', file_base)
		if num_match_base and num_match_file and num_match_base.group() == num_match_file.group():
			return os.path.join(target_dir, file)
		
		# Check for similar length and at least 70% character match
		if abs(len(clean_file_base) - len(clean_base_name)) <= 3:
			matching_chars = sum(1 for a, b in zip(clean_file_base, clean_base_name) if a == b)
			min_len = min(len(clean_file_base), len(clean_base_name))
			if min_len > 0 and matching_chars / min_len >= 0.7:
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
