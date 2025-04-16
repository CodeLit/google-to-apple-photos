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


def is_uuid_filename(filename: str) -> bool:
	"""
	Check if the filename follows the Apple UUID pattern like 1D259D70-974B-4D1C-921E-7F35783509C1_1_201_a.jpeg
	
	Args:
		filename: Filename to check
		
	Returns:
		True if the filename follows the UUID pattern, False otherwise
	"""
	# UUID pattern: 8-4-4-4-12 hex digits, possibly followed by modifiers
	uuid_pattern = re.compile(r'^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}(_\d+)*(_\d+)*(_[a-z])*\.[a-zA-Z0-9]+$', re.IGNORECASE)
	return bool(uuid_pattern.match(filename))


def are_duplicate_filenames(filename1: str, filename2: str) -> bool:
	"""
	Check if two filenames are duplicates (same base name but different extensions)
	
	Args:
		filename1: First filename
		filename2: Second filename
		
	Returns:
		True if the filenames are duplicates, False otherwise
	"""
	base_name1, ext1 = os.path.splitext(filename1)
	base_name2, ext2 = os.path.splitext(filename2)
	
	# If both are UUID-style filenames, they're duplicates if the UUIDs match
	if is_uuid_filename(filename1) and is_uuid_filename(filename2):
		# Extract just the UUID part (before any underscores)
		uuid1 = base_name1.split('_')[0]
		uuid2 = base_name2.split('_')[0]
		return uuid1.lower() == uuid2.lower()
	
	# For regular filenames, they're duplicates if the base names match
	return base_name1.lower() == base_name2.lower() and ext1.lower() != ext2.lower()


def extract_date_from_filename(file_path: str) -> Optional[Tuple[str, str]]:
	"""
	Extract date from filename patterns like IMG-YYYYMMDD-WA0012.jpg or 2021-03-07_23-15-52.jpg
	
	Args:
		file_path: Path to the file
		
	Returns:
		Tuple of (date string in YYYY:MM:DD format, match pattern description) or None if no match
	"""
	filename = os.path.basename(file_path)
	
	# Match IMG-YYYYMMDD pattern (e.g., IMG-20161231-WA0012.jpg)
	img_date_match = re.match(r'IMG-([0-9]{4})([0-9]{2})([0-9]{2}).*\..+', filename, re.IGNORECASE)
	if img_date_match:
		year = img_date_match.group(1)
		month = img_date_match.group(2)
		day = img_date_match.group(3)
		
		# Validate date components
		try:
			# Check if it's a valid date
			from datetime import datetime
			datetime(int(year), int(month), int(day))
			
			# Return formatted date string
			return f"{year}:{month}:{day}", "IMG-YYYYMMDD pattern"
		except ValueError:
			# Invalid date
			pass
	
	# Match YYYY-MM-DD_HH-MM-SS pattern (e.g., 2021-03-07_23-15-52.jpg)
	date_time_match = re.match(r'([0-9]{4}-[0-9]{2}-[0-9]{2})_([0-9]{2}-[0-9]{2}-[0-9]{2}).*\..+', filename)
	if date_time_match:
		date_str = date_time_match.group(1)  # YYYY-MM-DD
		time_str = date_time_match.group(2).replace('-', ':')  # HH:MM:SS
		
		# Validate date components
		try:
			# Check if it's a valid date
			from datetime import datetime
			date_obj = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M:%S')
			
			# Return formatted date string (YYYY:MM:DD)
			year, month, day = date_str.split('-')
			return f"{year}:{month}:{day}", "YYYY-MM-DD_HH-MM-SS pattern"
		except ValueError:
			# Invalid date
			pass
	
	# Match YYYYMMDD_HHMMSS pattern (e.g., 20210307_231552.jpg)
	date_time_compact_match = re.match(r'([0-9]{8})_([0-9]{6}).*\..+', filename)
	if date_time_compact_match:
		date_str = date_time_compact_match.group(1)  # YYYYMMDD
		time_str = date_time_compact_match.group(2)  # HHMMSS
		
		# Validate date components
		try:
			# Check if it's a valid date
			from datetime import datetime
			date_obj = datetime.strptime(f"{date_str} {time_str}", '%Y%m%d %H%M%S')
			
			# Return formatted date string (YYYY:MM:DD)
			year = date_str[0:4]
			month = date_str[4:6]
			day = date_str[6:8]
			return f"{year}:{month}:{day}", "YYYYMMDD_HHMMSS pattern"
		except ValueError:
			# Invalid date
			pass
	
	# Match WhatsApp pattern (e.g., IMG-20210307-WA0001.jpg)
	whatsapp_match = re.match(r'(?:IMG|VID)-([0-9]{4})([0-9]{2})([0-9]{2})-WA[0-9]+\..+', filename, re.IGNORECASE)
	if whatsapp_match:
		year = whatsapp_match.group(1)
		month = whatsapp_match.group(2)
		day = whatsapp_match.group(3)
		
		# Validate date components
		try:
			# Check if it's a valid date
			from datetime import datetime
			datetime(int(year), int(month), int(day))
			
			# Return formatted date string
			return f"{year}:{month}:{day}", "WhatsApp pattern"
		except ValueError:
			# Invalid date
			pass
	
	# Match Screenshot pattern (e.g., Screenshot_20210307-231552.jpg)
	screenshot_match = re.match(r'Screenshot_([0-9]{8})-([0-9]{6}).*\..+', filename, re.IGNORECASE)
	if screenshot_match:
		date_str = screenshot_match.group(1)  # YYYYMMDD
		time_str = screenshot_match.group(2)  # HHMMSS
		
		# Validate date components
		try:
			# Check if it's a valid date
			from datetime import datetime
			date_obj = datetime.strptime(f"{date_str} {time_str}", '%Y%m%d %H%M%S')
			
			# Return formatted date string (YYYY:MM:DD)
			year = date_str[0:4]
			month = date_str[4:6]
			day = date_str[6:8]
			return f"{year}:{month}:{day}", "Screenshot pattern"
		except ValueError:
			# Invalid date
			pass
	
	# Match Google Takeout IMG pattern (e.g., IMG20210503102138.jpg or IMG20210503102004_06.jpg)
	google_img_match = re.match(r'(?:IMG|VID)([0-9]{4})([0-9]{2})([0-9]{2})([0-9]{6})(?:_[0-9]+)?\..+', filename, re.IGNORECASE)
	if google_img_match:
		year = google_img_match.group(1)
		month = google_img_match.group(2)
		day = google_img_match.group(3)
		time_str = google_img_match.group(4)  # HHMMSS
		
		# Validate date components
		try:
			# Check if it's a valid date
			from datetime import datetime
			date_obj = datetime.strptime(f"{year}{month}{day} {time_str}", '%Y%m%d %H%M%S')
			
			# Return formatted date string
			return f"{year}:{month}:{day}", "Google Takeout pattern"
		except ValueError:
			# Invalid date
			pass
	
	return None


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
