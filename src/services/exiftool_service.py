"""
Service for interacting with exiftool
"""
import subprocess
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ExifToolService:
	"""Service for interacting with exiftool"""
	
	@staticmethod
	def check_exiftool() -> bool:
		"""
		Check if exiftool is installed
		
		Returns:
			True if exiftool is installed, False otherwise
		"""
		try:
			subprocess.run(['exiftool', '-ver'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
			return True
		except (subprocess.SubprocessError, FileNotFoundError):
			logger.error("exiftool is not installed. Please install it to continue.")
			logger.info("On macOS, you can install it with: brew install exiftool")
			return False
	
	@staticmethod
	def apply_metadata(file_path: str, metadata_args: List[str], dry_run: bool = False) -> bool:
		"""
		Apply metadata to a file using exiftool
		
		Args:
			file_path: Path to the file
			metadata_args: List of exiftool arguments
			dry_run: If True, only print the command without executing it
			
		Returns:
			True if successful, False otherwise
		"""
		if not metadata_args:
			return False
		
		try:
			cmd = ['exiftool']
			cmd.extend(metadata_args)
			
			# Overwrite original file
			cmd.extend(['-overwrite_original', file_path])
			
			if dry_run:
				logger.info(f"[DRY RUN] Would execute: {' '.join(cmd)}")
				return True
			
			result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
			
			if result.returncode == 0:
				logger.info(f"Successfully updated metadata for {file_path}")
				return True
			else:
				logger.error(f"Failed to update metadata for {file_path}: {result.stderr.decode()}")
				return False
		except Exception as e:
			logger.error(f"Error applying metadata to {file_path}: {str(e)}")
			return False
	
	@staticmethod
	def get_metadata(file_path: str) -> Optional[dict]:
		"""
		Get metadata from a file using exiftool
		
		Args:
			file_path: Path to the file
			
		Returns:
			Dictionary with metadata or None if failed
		"""
		try:
			cmd = ['exiftool', '-json', file_path]
			result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
			
			if result.returncode == 0:
				import json
				return json.loads(result.stdout)[0]
			else:
				logger.error(f"Failed to get metadata for {file_path}: {result.stderr}")
				return None
		except Exception as e:
			logger.error(f"Error getting metadata from {file_path}: {str(e)}")
			return None
