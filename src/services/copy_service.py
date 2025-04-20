import os
import shutil
import logging
from typing import List, Tuple, Dict, Set
from pathlib import Path

from src.utils.image_utils import is_media_file, compute_hash_for_file, load_image_hashes, save_image_hashes

logger = logging.getLogger(__name__)

class CopyService:
	"""Service for copying missing media files from old to new directory"""
	
	@staticmethod
	def copy_missing_files(old_dir: str, new_dir: str, dry_run: bool = False) -> Tuple[int, int]:
		"""
		Copy media files from old directory to new directory if they don't exist in new
		based on hash comparison to avoid duplicates
		
		Args:
			old_dir: Source directory with original files
			new_dir: Target directory where files should be copied
			dry_run: If True, only log what would be done without actually copying
			
		Returns:
			Tuple of (total files found, files copied)
		"""
		if not os.path.exists(old_dir):
			logger.error(f"Source directory not found: {old_dir}")
			return 0, 0
			
		if not os.path.exists(new_dir):
			logger.error(f"Target directory not found: {new_dir}")
			return 0, 0
		
		# Get all media files in old directory
		old_files = []
		for root, _, files in os.walk(old_dir):
			for file in files:
				file_path = os.path.join(root, file)
				if is_media_file(file_path) and not file.endswith('.json'):
					old_files.append(file_path)
		
		logger.info(f"Found {len(old_files)} media files in {old_dir}")
		
		# Get all media files in new directory
		new_files = []
		for root, _, files in os.walk(new_dir):
			for file in files:
				file_path = os.path.join(root, file)
				if is_media_file(file_path):
					new_files.append(file_path)
		
		logger.info(f"Found {len(new_files)} media files in {new_dir}")
		
		# Load hash caches for old and new directories
		logger.info("Loading hash caches...")
		old_hash_cache = load_image_hashes('data/old_image_hashes.csv')
		logger.info(f"Loaded {len(old_hash_cache)} hashes from old cache")
		
		new_hash_cache = load_image_hashes('data/new_image_hashes.csv')
		logger.info(f"Loaded {len(new_hash_cache)} hashes from new cache")
		
		# Compute hashes for files in new directory
		logger.info("Computing hashes for files in new directory...")
		new_file_hashes = {}
		for i, file_path in enumerate(new_files):
			# Use the new directory hash cache
			file_hash = compute_hash_for_file(file_path, new_hash_cache)
			if file_hash:
				new_file_hashes[file_hash] = file_path
			
			# Log progress every 500 files
			if (i + 1) % 500 == 0:
				logger.info(f"Computed hashes for {i + 1}/{len(new_files)} files in new directory")
				# Save new hash cache periodically
				save_image_hashes(new_hash_cache, 'data/new_image_hashes.csv')
		
		logger.info(f"Computed hashes for {len(new_file_hashes)} files in new directory")
		# Save new hash cache
		save_image_hashes(new_hash_cache, 'data/new_image_hashes.csv')
		
		# Find files that exist in old but not in new based on hash
		logger.info("Finding missing files based on hash comparison...")
		missing_files = []
		for i, old_file in enumerate(old_files):
			# Use the old directory hash cache
			file_hash = compute_hash_for_file(old_file, old_hash_cache)
			
			# If we couldn't compute a hash or the hash doesn't exist in new directory
			if not file_hash or file_hash not in new_file_hashes:
				missing_files.append(old_file)
			
			# Log progress every 500 files
			if (i + 1) % 500 == 0:
				logger.info(f"Processed {i + 1}/{len(old_files)} files from old directory")
				# Save old hash cache periodically
				save_image_hashes(old_hash_cache, 'data/old_image_hashes.csv')
		
		# Save old hash cache
		save_image_hashes(old_hash_cache, 'data/old_image_hashes.csv')
		
		logger.info(f"Found {len(missing_files)} files in {old_dir} that don't exist in {new_dir} based on hash comparison")
		
		# Copy missing files
		copied_count = 0
		for old_file in missing_files:
			filename = os.path.basename(old_file)
			new_file = os.path.join(new_dir, filename)
			
			if dry_run:
				logger.info(f"[DRY RUN] Would copy {old_file} to {new_file}")
				copied_count += 1
			else:
				try:
					shutil.copy2(old_file, new_file)
					logger.info(f"Copied {old_file} to {new_file}")
					copied_count += 1
					
					# Log progress every 100 files
					if copied_count % 100 == 0:
						logger.info(f"Copied {copied_count} of {len(missing_files)} files")
				except Exception as e:
					logger.error(f"Error copying {old_file} to {new_file}: {str(e)}")
		
		logger.info(f"Copied {copied_count} files from {old_dir} to {new_dir}")
		return len(missing_files), copied_count
