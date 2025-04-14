"""
Utility functions for image processing, hashing and duplicate detection
"""
import os
import logging
from typing import Dict, List, Tuple, Set, Optional
from pathlib import Path
import imagehash
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

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
		return None
	except Exception as e:
		logger.debug(f"Unexpected error computing hash for {image_path}: {str(e)}")
		return None

def compute_hash_for_file(file_path: str) -> Optional[str]:
	"""
	Compute hash for a file (image or video).
	For images, use perceptual hash.
	For videos, use file size and first few bytes as a simple hash.
	
	Args:
		file_path: Path to the file
		
	Returns:
		String representation of the hash or None if failed
	"""
	if is_image_file(file_path):
		return compute_image_hash(file_path)
	elif is_video_file(file_path):
		try:
			# For videos, use file size and first few bytes as a simple hash
			file_size = os.path.getsize(file_path)
			with open(file_path, 'rb') as f:
				first_bytes = f.read(1024)  # Read first 1KB
				
			import hashlib
			m = hashlib.md5()
			m.update(str(file_size).encode())
			m.update(first_bytes)
			return m.hexdigest()
		except Exception as e:
			logger.debug(f"Could not compute hash for video {file_path}: {str(e)}")
			return None
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

def find_duplicates(directory: str, similarity_threshold: float = 0.98) -> Dict[str, List[str]]:
	"""
	Find duplicate images in a directory based on perceptual hashing.
	
	Args:
		directory: Directory to search for duplicates
		similarity_threshold: Threshold for considering images as duplicates (0.0 to 1.0)
		
	Returns:
		Dictionary mapping original files to lists of duplicate files
	"""
	hashes = {}  # Map hash to file path
	duplicates = {}  # Map original file to list of duplicate files
	
	# First pass: compute hashes for all images
	for root, _, files in os.walk(directory):
		for file in files:
			file_path = os.path.join(root, file)
			if is_media_file(file_path):
				file_hash = compute_hash_for_file(file_path)
				if file_hash:
					if file_hash not in hashes:
						hashes[file_hash] = file_path
					else:
						# Exact hash match - definite duplicate
						original = hashes[file_hash]
						if original not in duplicates:
							duplicates[original] = []
						duplicates[original].append(file_path)
	
	# Second pass: check for similar (but not identical) images
	hash_items = list(hashes.items())
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
	
	return duplicates

def find_matching_file_by_hash(source_file: str, target_dir: str, 
							  similarity_threshold: float = 0.98) -> Optional[str]:
	"""
	Find a matching file in target_dir based on perceptual hash similarity.
	
	Args:
		source_file: Source file to match
		target_dir: Directory to search for matches
		similarity_threshold: Threshold for considering files as matches (0.0 to 1.0)
		
	Returns:
		Path to the matching file or None if not found
	"""
	if not os.path.exists(source_file) or not os.path.isdir(target_dir):
		return None
		
	# Compute hash for source file
	source_hash = compute_hash_for_file(source_file)
	if not source_hash:
		return None
		
	best_match = None
	best_similarity = 0.0
	
	# Check all files in target directory
	for root, _, files in os.walk(target_dir):
		for file in files:
			target_file = os.path.join(root, file)
			if is_media_file(target_file):
				target_hash = compute_hash_for_file(target_file)
				if target_hash:
					similarity = hash_similarity(source_hash, target_hash)
					if similarity >= similarity_threshold and similarity > best_similarity:
						best_match = target_file
						best_similarity = similarity
	
	if best_match:
		logger.debug(f"Found match for {source_file} -> {best_match} (similarity: {best_similarity:.2f})")
		
	return best_match
