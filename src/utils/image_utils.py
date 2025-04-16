"""
Utility functions for image processing, hashing and duplicate detection
"""
import os
import logging
import hashlib
import concurrent.futures
from typing import Dict, List, Tuple, Set, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import optional dependencies
HAS_IMAGE_HASH = False
try:
	import imagehash
	from PIL import Image, UnidentifiedImageError
	HAS_IMAGE_HASH = True
except ImportError:
	logger.warning("imagehash or Pillow not installed. Using basic file matching instead of image hash matching.")

# Supported image formats
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.tiff', '.tif', '.bmp', '.gif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.m4v', '.3gp'}

def is_image_file(file_path: str) -> bool:
	"""Check if a file is an image based on its extension"""
	ext = os.path.splitext(file_path)[1].lower()
	return ext in IMAGE_EXTENSIONS

def is_video_file(file_path: str) -> bool:
	"""Check if a file is a video based on its extension"""
	ext = os.path.splitext(file_path)[1].lower()
	return ext in VIDEO_EXTENSIONS

def is_media_file(file_path: str) -> bool:
	"""Check if a file is a media file (image or video)"""
	return is_image_file(file_path) or is_video_file(file_path)

def compute_image_hash(image_path: str, hash_size: int = 8) -> Optional[str]:
	"""
	Compute perceptual hash for an image.
	
	Args:
		image_path: Path to the image file
		hash_size: Size of the hash (default: 8)
		
	Returns:
		String representation of the hash or None if failed
	"""
	if not HAS_IMAGE_HASH:
		# Fall back to simple file hash if imagehash is not available
		return compute_file_hash(image_path)
		
	try:
		if not is_image_file(image_path):
			return None
			
		img = Image.open(image_path)
		# Convert to grayscale to avoid color space issues
		if img.mode != 'L':
			img = img.convert('L')
			
		# Compute perceptual hash
		phash = imagehash.phash(img, hash_size=hash_size)
		return str(phash)
	except (UnidentifiedImageError, IOError, OSError) as e:
		logger.debug(f"Could not compute hash for {image_path}: {str(e)}")
		return compute_file_hash(image_path)  # Fall back to file hash
	except Exception as e:
		logger.debug(f"Unexpected error computing hash for {image_path}: {str(e)}")
		return compute_file_hash(image_path)  # Fall back to file hash


def compute_file_hash(file_path: str) -> Optional[str]:
	"""
	Compute a simple hash based on file size and first few bytes
	
	Args:
		file_path: Path to the file
		
	Returns:
		String representation of the hash or None if failed
	"""
	try:
		# Use file size and first few bytes as a simple hash
		file_size = os.path.getsize(file_path)
		with open(file_path, 'rb') as f:
			first_bytes = f.read(1024)  # Read first 1KB
			
		m = hashlib.md5()
		m.update(str(file_size).encode())
		m.update(first_bytes)
		return m.hexdigest()
	except Exception as e:
		logger.debug(f"Could not compute file hash for {file_path}: {str(e)}")
		return None

def compute_hash_for_file(file_path: str) -> Optional[str]:
	"""
	Compute hash for a file (image or video).
	For images, use perceptual hash if available, otherwise use file hash.
	For videos, use file size and first few bytes as a simple hash.
	
	Args:
		file_path: Path to the file
		
	Returns:
		String representation of the hash or None if failed
	"""
	if is_image_file(file_path):
		return compute_image_hash(file_path)
	elif is_video_file(file_path):
		return compute_file_hash(file_path)
	else:
		return None

def hash_similarity(hash1: str, hash2: str) -> float:
	"""
	Calculate similarity between two image hashes.
	
	Args:
		hash1: First hash string
		hash2: Second hash string
		
	Returns:
		Similarity score between 0.0 and 1.0
	"""
	if not hash1 or not hash2:
		return 0.0
		
	# If hashes are identical, return 1.0
	if hash1 == hash2:
		return 1.0
		
	if HAS_IMAGE_HASH and hash1.startswith('0x') and hash2.startswith('0x'):
		try:
			# Convert string hashes back to imagehash objects
			h1 = imagehash.hex_to_hash(hash1) if isinstance(hash1, str) else hash1
			h2 = imagehash.hex_to_hash(hash2) if isinstance(hash2, str) else hash2
			
			# Calculate hamming distance
			distance = h1 - h2
			max_distance = len(h1.hash) * len(h1.hash[0])  # Maximum possible distance
			
			# Convert distance to similarity score (0.0 to 1.0)
			similarity = 1.0 - (distance / max_distance)
			return similarity
		except Exception as e:
			logger.debug(f"Error calculating hash similarity: {str(e)}")
			return 0.0
	else:
		# For MD5 hashes, we can only check equality
		# Return a binary similarity (1.0 if equal, 0.0 if different)
		return 1.0 if hash1 == hash2 else 0.0

def check_metadata_status(old_dir: str, new_dir: str, status_log: str = 'metadata_status.log') -> Tuple[int, int, int]:
	"""
	Check which files in the new directory need metadata updates from the old directory
	
	Args:
		old_dir: Directory with Google Takeout files
		new_dir: Directory with Apple Photos exports
		status_log: Path to the log file to write the results to
		
	Returns:
		Tuple of (total files in new, files with metadata in old, files without metadata in old)
	"""
	logger.info(f"Checking metadata status for files in {new_dir}...")
	
	# Get all media files in the new directory
	new_files = []
	for root, _, files in os.walk(new_dir):
		for filename in files:
			file_path = os.path.join(root, filename)
			if is_media_file(file_path):
				new_files.append(file_path)
	
	logger.info(f"Found {len(new_files)} media files in {new_dir}")
	
	# Pre-index all JSON files in the old directory
	logger.info(f"Indexing JSON files in {old_dir}...")
	json_files_map = {}
	json_count = 0
	
	for root, _, files in os.walk(old_dir):
		for filename in files:
			if filename.endswith('.json'):
				json_path = os.path.join(root, filename)
				json_count += 1
				
				# Store the JSON file path with the base filename as key
				# Remove the .supplemental-metadata.json suffix if present
				base_name = filename
				if '.supplemental-metadata.json' in filename:
					base_name = filename.replace('.supplemental-metadata.json', '')
				elif '.json' in filename:
					base_name = filename.replace('.json', '')
				
				# Add to map with both the full name and potential base name
				json_files_map[filename] = json_path
				json_files_map[base_name] = json_path
	
	logger.info(f"Indexed {json_count} JSON files from {old_dir}")
	
	# Find corresponding JSON files in the old directory
	files_with_metadata = []
	files_without_metadata = []
	
	for new_file in new_files:
		new_filename = os.path.basename(new_file)
		json_found = False
		
		# Check if we have a matching JSON file
		potential_matches = [
			new_filename + '.supplemental-metadata.json',
			new_filename + '.json',
			new_filename
		]
		
		for match in potential_matches:
			if match in json_files_map:
				json_path = json_files_map[match]
				
				# Check if the JSON file contains photoTakenTime
				try:
					import json
					with open(json_path, 'r', encoding='utf-8') as f:
						metadata = json.load(f)
						if 'photoTakenTime' in metadata:
							files_with_metadata.append((new_file, json_path))
							json_found = True
							break
				except Exception as e:
					logger.error(f"Error reading JSON file {json_path}: {str(e)}")
					continue
		
		if not json_found:
			files_without_metadata.append(new_file)
	
	logger.info(f"Found metadata for {len(files_with_metadata)} files")
	logger.info(f"Missing metadata for {len(files_without_metadata)} files")
	
	# Write to log file
	with open(status_log, 'w', encoding='utf-8') as f:
		f.write("# Files with metadata available\n")
		f.write("new_file,json_file\n")
		for new_file, json_path in files_with_metadata:
			f.write(f"{new_file},{json_path}\n")
		
		f.write("\n# Files without metadata\n")
		for new_file in files_without_metadata:
			f.write(f"{new_file}\n")
	
	logger.info(f"Metadata status written to {status_log}")
	return len(new_files), len(files_with_metadata), len(files_without_metadata)


def find_duplicates_by_name(directory: str, suffix: str = ' (1)', dry_run: bool = False, duplicates_log: str = 'name_duplicates.log') -> Tuple[int, int]:
	"""
	Find duplicates by checking for files with the same base name but with a suffix,
	and optionally remove the duplicates with the suffix
	
	Args:
		directory: Directory containing files to check
		suffix: Suffix to look for (default: ' (1)')
		dry_run: If True, only print what would be done without actually removing files
		duplicates_log: Path to the log file to write the results to
		
	Returns:
		Tuple of (number of duplicates found, number of duplicates removed)
	"""
	logger.info(f"Finding duplicates by name in {directory}...")
	
	# Find potential duplicates
	potential_duplicates = find_potential_duplicates(directory, suffix)
	
	if not potential_duplicates:
		logger.info("No potential duplicates found")
		return 0, 0
	
	logger.info(f"Found {len(potential_duplicates)} potential duplicate pairs")
	
	# Compare file sizes to confirm they are duplicates
	confirmed_duplicates = {}
	for original, duplicate in potential_duplicates.items():
		# Get file sizes
		orig_size = os.path.getsize(original)
		dup_size = os.path.getsize(duplicate)
		
		# If file sizes match, they are likely duplicates
		if orig_size == dup_size:
			confirmed_duplicates[original] = duplicate
	
	logger.info(f"Confirmed {len(confirmed_duplicates)} duplicate pairs by file size")
	
	# Write to log file
	with open(duplicates_log, 'w') as f:
		f.write("original_file,duplicate_file\n")
		for original, duplicate in confirmed_duplicates.items():
			f.write(f"{original},{duplicate}\n")
	
	logger.info(f"Duplicate information written to {duplicates_log}")
	
	# Remove duplicates if not in dry run mode
	removed = 0
	if not dry_run:
		for _, duplicate in confirmed_duplicates.items():
			try:
				os.remove(duplicate)
				logger.debug(f"Removed duplicate: {duplicate}")
				removed += 1
				
				# Log progress every 100 files
				if removed % 100 == 0:
					logger.info(f"Removed {removed} duplicates so far")
			except Exception as e:
				logger.error(f"Error removing {duplicate}: {str(e)}")
		logger.info(f"Removed {removed} duplicate files")
	else:
		logger.info(f"[DRY RUN] Would remove {len(confirmed_duplicates)} duplicate files")
	
	return len(confirmed_duplicates), removed


def find_duplicates(directory: str, similarity_threshold: float = 0.98, duplicates_log: str = 'duplicates.log') -> Dict[str, List[str]]:
	"""
	Find duplicate images in a directory based on perceptual hashing.
	Uses parallel processing and optimized algorithms for faster performance.
	
	Args:
		directory: Directory to search for duplicates
		similarity_threshold: Threshold for considering images as duplicates (0.0 to 1.0)
		
	Returns:
		Dictionary mapping original files to lists of duplicate files
	"""
	import concurrent.futures
	from collections import defaultdict
	
	duplicates = {}  # Map original file to list of duplicate files
	media_files = []
	
	# Collect all media files first
	logger.info(f"Collecting media files from {directory}...")
	for root, _, files in os.walk(directory):
		for file in files:
			file_path = os.path.join(root, file)
			if is_media_file(file_path):
				media_files.append(file_path)
	
	logger.info(f"Found {len(media_files)} media files. Computing hashes...")
	
	# Group files by size first (quick filter)
	size_groups = defaultdict(list)
	for file_path in media_files:
		try:
			file_size = os.path.getsize(file_path)
			# Only group files if they're within 5% size of each other
			size_key = file_size // (1024 * 10)  # Group by 10KB chunks
			size_groups[size_key].append(file_path)
		except (OSError, IOError) as e:
			logger.debug(f"Error getting size for {file_path}: {str(e)}")
	
	# Filter groups with only one file
	potential_duplicate_groups = {size: files for size, files in size_groups.items() if len(files) > 1}
	logger.info(f"Found {len(potential_duplicate_groups)} groups of files with similar sizes")
	
	# Function to compute hash for a file
	def compute_hash_for_file_wrapper(file_path):
		try:
			return file_path, compute_hash_for_file(file_path)
		except Exception as e:
			logger.debug(f"Error computing hash for {file_path}: {str(e)}")
			return file_path, None
	
	# Process each group in parallel
	with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
		for size_key, files in potential_duplicate_groups.items():
			# Compute hashes for all files in this group
			hash_results = list(executor.map(compute_hash_for_file_wrapper, files))
			
			# Group files by hash
			hash_groups = defaultdict(list)
			for file_path, file_hash in hash_results:
				if file_hash:
					hash_groups[file_hash].append(file_path)
			
			# Add exact hash matches to duplicates
			for file_hash, file_paths in hash_groups.items():
				if len(file_paths) > 1:
					# Sort by modification time to keep the oldest file as original
					file_paths.sort(key=lambda f: os.path.getmtime(f))
					original = file_paths[0]
					if original not in duplicates:
						duplicates[original] = []
					duplicates[original].extend(file_paths[1:])
			
			# If using perceptual hashing, check for similar (but not identical) images
			if HAS_IMAGE_HASH:
				# Only compare hashes between different groups
				hash_items = [(h, f) for h, files in hash_groups.items() 
							 for f in files if len(files) == 1 and is_image_file(f)]
				
				# Skip small groups
				if len(hash_items) <= 1:
					continue
				
				# Compare each pair of hashes
				for i in range(len(hash_items)):
					hash1, file1 = hash_items[i]
					
					# Skip if this file is already marked as a duplicate
					if any(file1 in dups for dups in duplicates.values()):
						continue
						
					for j in range(i + 1, len(hash_items)):
						hash2, file2 = hash_items[j]
						
						# Skip if this file is already marked as a duplicate
						if any(file2 in dups for dups in duplicates.values()):
							continue
							
						# Check similarity
						similarity = hash_similarity(hash1, hash2)
						if similarity >= similarity_threshold:
							# Determine which file to keep as original (e.g., keep the older file)
							original = file1
							duplicate = file2
							
							if os.path.getmtime(file2) < os.path.getmtime(file1):
								original = file2
								duplicate = file1
							
							if original not in duplicates:
								duplicates[original] = []
							duplicates[original].append(duplicate)
	
	logger.info(f"Found {sum(len(dups) for dups in duplicates.values())} duplicate files in {len(duplicates)} groups")
	return duplicates

# Cache for file hashes to avoid recomputing
_file_hash_cache = {}

def find_potential_duplicates(directory: str, suffix: str = ' (1)') -> Dict[str, str]:
	"""
	Find potential duplicates by checking for files with the same base name but with different extensions
	or with a suffix like ' (1)' or UUID-style duplicates
	
	Args:
		directory: Directory containing files to check
		suffix: Suffix to look for (default: ' (1)')
		
	Returns:
		Dictionary mapping original files to potential duplicates
	"""
	from src.utils.file_utils import are_duplicate_filenames, is_uuid_filename, get_base_filename
	
	if not os.path.exists(directory):
		logger.error(f"Directory not found: {directory}")
		return {}
	
	# Get all files in the directory
	all_files = []
	for root, _, files in os.walk(directory):
		for filename in files:
			all_files.append(os.path.join(root, filename))
	
	# Create a lookup dictionary for faster searching
	file_lookup = {os.path.basename(f): f for f in all_files}
	
	# Find potential duplicates
	potential_duplicates = {}
	
	# First, check for traditional suffix-based duplicates
	for filename, file_path in file_lookup.items():
		if suffix in filename:
			continue  # Skip files that already have the suffix
		
		# Check if there's a file with the same name + suffix
		dup_filename = filename.split('.')[0] + suffix + '.' + filename.split('.')[-1]
		if dup_filename in file_lookup:
			potential_duplicates[file_path] = file_lookup[dup_filename]
			logger.debug(f"Found suffix-based duplicate: {filename} -> {dup_filename}")
	
	# Now check for extension-based duplicates and UUID-style duplicates
	processed_pairs = set()  # To avoid processing the same pair twice
	for i, file1 in enumerate(all_files):
		filename1 = os.path.basename(file1)
		for file2 in all_files[i+1:]:
			filename2 = os.path.basename(file2)
			
			# Skip if we've already processed this pair
			pair_key = f"{file1}|{file2}"
			if pair_key in processed_pairs:
				continue
			
			# Check if they're duplicates based on our custom detection
			if are_duplicate_filenames(filename1, filename2):
				# Prefer non-UUID filenames as the "original"
				if is_uuid_filename(filename1) and not is_uuid_filename(filename2):
					potential_duplicates[file2] = file1
					logger.debug(f"Found extension/UUID duplicate: {filename2} -> {filename1}")
				else:
					potential_duplicates[file1] = file2
					logger.debug(f"Found extension/UUID duplicate: {filename1} -> {filename2}")
				
				# Mark this pair as processed
				processed_pairs.add(pair_key)
				processed_pairs.add(f"{file2}|{file1}")  # Add reverse pair too
	
	logger.info(f"Found {len(potential_duplicates)} potential duplicate pairs")
	return potential_duplicates


def rename_files_remove_suffix(directory: str, suffix: str = ' (1)', dry_run: bool = False) -> Tuple[int, int]:
	"""
	Rename files in directory by removing a specific suffix from filenames
	
	Args:
		directory: Directory containing files to rename
		suffix: Suffix to remove from filenames (default: ' (1)')
		dry_run: If True, only print what would be done without actually renaming files
		
	Returns:
		Tuple of (number of files processed, number of files renamed)
	"""
	if not os.path.exists(directory):
		logger.error(f"Directory not found: {directory}")
		return 0, 0
	
	processed = 0
	renamed = 0
	
	logger.info(f"Scanning for files with suffix '{suffix}' in {directory}")
	
	for root, _, files in os.walk(directory):
		for filename in files:
			if suffix in filename:
				old_path = os.path.join(root, filename)
				new_filename = filename.replace(suffix, '')
				new_path = os.path.join(root, new_filename)
				
				processed += 1
				
				# Check if the destination file already exists
				if os.path.exists(new_path):
					logger.warning(f"Cannot rename {filename} to {new_filename} - destination file already exists")
					continue
				
				if dry_run:
					logger.info(f"[DRY RUN] Would rename: {filename} -> {new_filename}")
				else:
					try:
						os.rename(old_path, new_path)
						logger.debug(f"Renamed: {filename} -> {new_filename}")
						renamed += 1
						
						# Log progress every 100 files
						if renamed % 100 == 0:
							logger.info(f"Renamed {renamed} files so far")
					except Exception as e:
						logger.error(f"Error renaming {filename}: {str(e)}")
	
	logger.info(f"Renaming complete. Processed {processed} files, renamed {renamed} files")
	return processed, renamed

def remove_duplicates(duplicates_log_path: str, dry_run: bool = False) -> Tuple[int, int]:
	"""
	Remove duplicate files based on the duplicates log file
	
	Args:
		duplicates_log_path: Path to the duplicates log file
		dry_run: If True, only print what would be done without actually removing files
		
	Returns:
		Tuple of (number of duplicates processed, number of duplicates removed)
	"""
	if not os.path.exists(duplicates_log_path):
		logger.error(f"Duplicates log file not found: {duplicates_log_path}")
		return 0, 0
	
	import csv
	
	duplicates_processed = 0
	duplicates_removed = 0
	
	try:
		with open(duplicates_log_path, 'r', newline='') as f:
			reader = csv.reader(f)
			# Skip header if present
			first_row = next(reader, None)
			if first_row and first_row[0].lower() == 'original':
				pass  # Skip header
			else:
				# Go back to the beginning if there was no header
				f.seek(0)
				reader = csv.reader(f)
			
			for row in reader:
				if len(row) < 2:
					continue
				
				original, duplicate = row
				duplicates_processed += 1
				
				# Check if both files exist
				if not os.path.exists(original):
					logger.warning(f"Original file not found: {original}")
					continue
				
				if not os.path.exists(duplicate):
					logger.warning(f"Duplicate file not found: {duplicate}")
					continue
				
				# Remove the duplicate
				if dry_run:
					logger.info(f"[DRY RUN] Would remove duplicate: {duplicate}")
					duplicates_removed += 1
				else:
					try:
						os.remove(duplicate)
						logger.info(f"Removed duplicate: {duplicate}")
						duplicates_removed += 1
					except Exception as e:
						logger.error(f"Error removing duplicate {duplicate}: {str(e)}")
	
		logger.info(f"Processed {duplicates_processed} duplicates, removed {duplicates_removed} files")
		return duplicates_processed, duplicates_removed
		
	except Exception as e:
		logger.error(f"Error processing duplicates log: {str(e)}")
		return duplicates_processed, duplicates_removed

def find_matching_file_by_hash(source_file: str, target_dir: str, 
						  similarity_threshold: float = 0.98, 
						  file_list: Optional[List[str]] = None) -> Optional[str]:
	"""
	Find a matching file in target_dir based on hash similarity.
	If imagehash is available, uses perceptual hash for images.
	Otherwise, falls back to simple file hash comparison.
	
	Args:
		source_file: Source file to match
		target_dir: Directory to search for matches
		similarity_threshold: Threshold for considering files as matches (0.0 to 1.0)
		file_list: Optional pre-populated list of files to search through
		
	Returns:
		Path to the matching file or None if not found
	"""
	if not os.path.exists(source_file):
		return None
	
	# Try exact filename match first (fastest)
	source_basename = os.path.basename(source_file)
	source_name, source_ext = os.path.splitext(source_basename)
	
	# Check if there's an exact match by filename
	if file_list is not None:
		for target_file in file_list:
			target_basename = os.path.basename(target_file)
			if target_basename == source_basename:
				return target_file
			
			# Try matching without extension (e.g., IMG_1234.jpg vs IMG_1234.jpeg)
			target_name, _ = os.path.splitext(target_basename)
			if target_name == source_name:
				return target_file
	
	# Compute hash for source file
	if source_file in _file_hash_cache:
		source_hash = _file_hash_cache[source_file]
	else:
		source_hash = compute_hash_for_file(source_file)
		_file_hash_cache[source_file] = source_hash
	
	if not source_hash:
		return None
		
	best_match = None
	best_similarity = 0.0
	
	# Use provided file list or scan directory
	target_files = file_list if file_list is not None else []
	if not target_files and os.path.isdir(target_dir):
		for root, _, files in os.walk(target_dir):
			for file in files:
				target_file = os.path.join(root, file)
				if is_media_file(target_file):
					target_files.append(target_file)
	
	# Process files in batches for better performance
	batch_size = 100
	for i in range(0, len(target_files), batch_size):
		batch = target_files[i:i+batch_size]
		
		# Process batch in parallel
		with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
			hash_futures = {}
			for target_file in batch:
				if target_file not in _file_hash_cache:
					hash_futures[executor.submit(compute_hash_for_file, target_file)] = target_file
			
			for future in concurrent.futures.as_completed(hash_futures):
				target_file = hash_futures[future]
				try:
					target_hash = future.result()
					_file_hash_cache[target_file] = target_hash
				except Exception as e:
					logger.debug(f"Error computing hash for {target_file}: {str(e)}")
					continue
		
		# Compare hashes
		for target_file in batch:
			if target_file in _file_hash_cache:
				target_hash = _file_hash_cache[target_file]
				if target_hash:
					similarity = hash_similarity(source_hash, target_hash)
					if similarity >= similarity_threshold and similarity > best_similarity:
						best_match = target_file
						best_similarity = similarity
						
						# If we have an exact match, no need to continue
						if similarity >= 0.99:
							break
	
	if best_match:
		logger.debug(f"Found match for {source_file} -> {best_match} (similarity: {best_similarity:.2f})")
		
	return best_match
