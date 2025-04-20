import os
import shutil
import logging
from typing import List, Tuple, Dict, Set
from pathlib import Path

from src.utils.image_utils import is_media_file

logger = logging.getLogger(__name__)

class CopyService:
	"""Service for copying missing media files from old to new directory"""
	
	@staticmethod
	def copy_missing_files(old_dir: str, new_dir: str, dry_run: bool = False) -> Tuple[int, int]:
		"""
		Copy media files from old directory to new directory if they don't exist in new
		
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
		
		# Create a set of filenames in new directory for faster lookup
		new_filenames = {os.path.basename(f) for f in new_files}
		
		# Find files that exist in old but not in new
		missing_files = []
		for old_file in old_files:
			filename = os.path.basename(old_file)
			if filename not in new_filenames:
				missing_files.append(old_file)
		
		logger.info(f"Found {len(missing_files)} files in {old_dir} that don't exist in {new_dir}")
		
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
