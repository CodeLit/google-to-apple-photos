import os
import shutil
import logging
import zipfile
import tempfile
from typing import List, Tuple, Dict, Set, Optional
from pathlib import Path

from src.utils.image_utils import is_media_file, compute_hash_for_file, load_image_hashes, save_image_hashes

logger = logging.getLogger(__name__)

class CopyService:
	"""Service for copying missing media files from old to new directory"""

	@staticmethod
	def is_zip_file(file_path: str) -> bool:
		"""
		Check if a file is a zip file

		Args:
			file_path: Path to the file

		Returns:
			True if the file is a zip file, False otherwise
		"""
		return os.path.isfile(file_path) and zipfile.is_zipfile(file_path)

	@staticmethod
	def extract_zip_file(zip_path: str, extract_dir: Optional[str] = None) -> str:
		"""
		Extract a zip file to a directory

		Args:
			zip_path: Path to the zip file
			extract_dir: Directory to extract to (if None, a temporary directory is created)

		Returns:
			Path to the directory where the zip file was extracted
		"""
		if not CopyService.is_zip_file(zip_path):
			logger.error(f"Not a valid zip file: {zip_path}")
			return ""

		try:
			# Create a temporary directory if extract_dir is not provided
			if not extract_dir:
				extract_dir = tempfile.mkdtemp(prefix="google_takeout_")
				logger.info(f"Created temporary directory for extraction: {extract_dir}")
			elif not os.path.exists(extract_dir):
				os.makedirs(extract_dir, exist_ok=True)
				logger.info(f"Created directory for extraction: {extract_dir}")

			# Extract the zip file
			logger.info(f"Extracting {zip_path} to {extract_dir}...")
			with zipfile.ZipFile(zip_path, 'r') as zip_ref:
				# Get total number of files for progress reporting
				total_files = len(zip_ref.namelist())
				logger.info(f"Zip file contains {total_files} files")

				# Extract files with progress reporting
				for i, file in enumerate(zip_ref.namelist()):
					zip_ref.extract(file, extract_dir)
					if (i + 1) % 100 == 0 or (i + 1) == total_files:
						logger.info(f"Extracted {i + 1}/{total_files} files")

			logger.info(f"Successfully extracted {zip_path} to {extract_dir}")
			return extract_dir
		except Exception as e:
			logger.error(f"Error extracting {zip_path}: {str(e)}")
			return ""

	@staticmethod
	def process_zip_file(zip_path: str, new_dir: str, dry_run: bool = False) -> Tuple[int, int]:
		"""
		Process a Google Takeout zip file by extracting it and copying the files to the target directory

		Args:
			zip_path: Path to the zip file
			new_dir: Target directory where files should be copied
			dry_run: If True, only log what would be done without actually copying

		Returns:
			Tuple of (total files found, files copied)
		"""
		if not CopyService.is_zip_file(zip_path):
			logger.error(f"Not a valid zip file: {zip_path}")
			return 0, 0

		if not os.path.exists(new_dir):
			logger.error(f"Target directory not found: {new_dir}")
			return 0, 0

		try:
			# Extract the zip file to a temporary directory
			extract_dir = CopyService.extract_zip_file(zip_path)
			if not extract_dir:
				logger.error(f"Failed to extract {zip_path}")
				return 0, 0

			# Process the extracted files
			logger.info(f"Processing extracted files from {extract_dir}...")
			result = CopyService.copy_missing_files(extract_dir, new_dir, dry_run)

			# Clean up the temporary directory if it was created by us
			if "google_takeout_" in extract_dir:
				logger.info(f"Cleaning up temporary directory: {extract_dir}")
				shutil.rmtree(extract_dir, ignore_errors=True)

			return result
		except Exception as e:
			logger.error(f"Error processing zip file {zip_path}: {str(e)}")
			return 0, 0

	@staticmethod
	def copy_missing_files(old_dir: str, new_dir: str, dry_run: bool = False) -> Tuple[int, int]:
		"""
		Copy media files from old directory to new directory if they don't exist in new
		based on hash comparison to avoid duplicates

		Args:
			old_dir: Source directory or zip file with original files
			new_dir: Target directory where files should be copied
			dry_run: If True, only log what would be done without actually copying

		Returns:
			Tuple of (total files found, files copied)
		"""
		# Check if old_dir is a zip file
		if CopyService.is_zip_file(old_dir):
			logger.info(f"Source is a zip file: {old_dir}")
			return CopyService.process_zip_file(old_dir, new_dir, dry_run)

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
		# Load combined image_hashes.csv and split into old/new
		hash_cache = load_image_hashes('data/image_hashes.csv')
		old_hash_cache = {k[4:]: v for k, v in hash_cache.items() if k.startswith('old:')}
		new_hash_cache = {k[4:]: v for k, v in hash_cache.items() if k.startswith('new:')}
		logger.info(f"Loaded {len(old_hash_cache)} old and {len(new_hash_cache)} new hashes from image_hashes.csv")

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
				save_image_hashes({**{f'old:{k}': v for k, v in old_hash_cache.items()}, **{f'new:{k}': v for k, v in new_hash_cache.items()}}, 'data/image_hashes.csv')

		logger.info(f"Computed hashes for {len(new_file_hashes)} files in new directory")
		# Save combined hash cache
		save_image_hashes({**{f'old:{k}': v for k, v in old_hash_cache.items()}, **{f'new:{k}': v for k, v in new_hash_cache.items()}}, 'data/image_hashes.csv')

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
				# Save combined hash cache periodically
				save_image_hashes({**{f'old:{k}': v for k, v in old_hash_cache.items()}, **{f'new:{k}': v for k, v in new_hash_cache.items()}}, 'data/image_hashes.csv')

		# Save combined hash cache
		save_image_hashes({**{f'old:{k}': v for k, v in old_hash_cache.items()}, **{f'new:{k}': v for k, v in new_hash_cache.items()}}, 'data/image_hashes.csv')

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
