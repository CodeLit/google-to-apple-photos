"""
Service for interacting with exiftool
"""
import subprocess
import logging
import os
import shutil
import mimetypes
from typing import List, Optional, Tuple

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
	def fix_file_extension(file_path: str) -> str:
		"""
		Fixes the file extension if it doesn't match the actual file type
		
		Args:
			file_path: Path to the file
			
		Returns:
			Path to the file with the correct extension (may be the same as input)
		"""
		if not os.path.exists(file_path):
			logger.error(f"File not found: {file_path}")
			return file_path
		
		real_ext, mime_type = ExifToolService.detect_file_type(file_path)
		if not real_ext:
			logger.debug(f"Could not determine real file type for {file_path}")
			return file_path
		
		# Get the current file extension
		file_ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
		
		# Check special case for JPG/JPEG
		if (real_ext.lower() == 'jpg' and file_ext.lower() == 'jpeg') or (real_ext.lower() == 'jpeg' and file_ext.lower() == 'jpg'):
			# Don't fix extension for JPG/JPEG as they are essentially the same format
			return file_path
		
		# If extension already matches the real file type
		if real_ext.lower() == file_ext.lower():
			return file_path
		
		# Correction map for different file types
		fix_map = {
			# Photos
			'jpg': ['heic', 'png', 'jfif', 'webp'],  # JPEG files with incorrect extensions
			'png': ['heic'],  # PNG files with incorrect extensions
			'heic': ['jpg', 'jpeg', 'png'],  # HEIC files with incorrect extensions
			# Videos
			'mp4': ['mov', 'avi', '3gp'],  # MP4 files with incorrect extensions
			'mov': ['mp4', 'avi', '3gp'],  # MOV files with incorrect extensions
		}
		
		# Check if we need to fix the extension
		if real_ext in fix_map and file_ext in fix_map.get(real_ext, []):
			# Create a new filename with the correct extension
			base_name = os.path.splitext(file_path)[0]
			new_path = f"{base_name}.{real_ext}"
			
			# Check if a file with this name already exists
			if os.path.exists(new_path):
				# Check the size of the existing file
				if os.path.getsize(new_path) > 0:
					logger.info(f"Using existing file with correct extension: {new_path}")
					# If the file already exists and is not empty, return its path
					return new_path
				else:
					# If the file exists but is empty, delete it
					try:
						os.remove(new_path)
						logger.info(f"Removed empty file with correct extension: {new_path}")
					except Exception as e:
						logger.error(f"Failed to remove empty file {new_path}: {str(e)}")
						return file_path
			
			try:
				# Create a copy of the file with the correct extension
				shutil.copy2(file_path, new_path)
				logger.info(f"Copied {file_path} to {new_path} with correct extension ({file_ext} -> {real_ext})")
				
				# Check that the copy was created successfully and has the correct size
				if os.path.exists(new_path) and os.path.getsize(new_path) > 0:
					# Remove the original file with incorrect extension
					try:
						os.remove(file_path)
						logger.info(f"Removed original file with incorrect extension: {file_path}")
					except Exception as e:
						logger.warning(f"Could not remove original file {file_path}: {str(e)}")
					return new_path
				else:
					logger.error(f"Failed to create valid copy with correct extension: {new_path}")
					# Remove the failed copy
					if os.path.exists(new_path):
						try:
							os.remove(new_path)
						except Exception:
							pass
					return file_path
			except Exception as e:
				logger.error(f"Error copying file {file_path} to {new_path}: {str(e)}")
				return file_path
		
		# If the file type doesn't need correction or is not supported
		return file_path

	@staticmethod
	def detect_file_type(file_path: str) -> Tuple[str, str]:
		"""
		Detects the actual file type, regardless of extension
		
		Args:
			file_path: Path to the file
			
		Returns:
			Tuple (real_extension, mime_type)
		"""
		if not os.path.exists(file_path):
			logger.error(f"File not found: {file_path}")
			return '', ''
		
		# Extended MIME-type map
		ext_map = {
			'image/jpeg': 'jpg',
			'image/jpg': 'jpg',
			'image/png': 'png',
			'image/heic': 'heic',
			'image/heif': 'heif',
			'video/mp4': 'mp4',
			'video/quicktime': 'mov',
			'video/mpeg': 'mpg',
			'video/x-msvideo': 'avi',
			'image/gif': 'gif',
			'image/webp': 'webp',
			'image/tiff': 'tiff'
		}
		
		try:
			# Method 1: Use exiftool to determine file type
			cmd = ['exiftool', '-FileType', '-s3', file_path]
			result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
			
			if result.returncode == 0 and result.stdout.strip():
				real_ext = result.stdout.strip().lower()
				
				# Get MIME type based on the real extension
				mime_type = mimetypes.guess_type(f"file.{real_ext}")[0] or ''
				
				# Check special cases
				if real_ext.lower() == 'jpeg':
					real_ext = 'jpg'
				
				return real_ext, mime_type
			
			# Method 2: If exiftool failed to determine the type, use file command
			cmd = ['file', '--mime-type', '-b', file_path]
			result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
			
			if result.returncode == 0 and result.stdout.strip():
				mime_type = result.stdout.strip()
				
				# Convert MIME type to extension
				real_ext = ext_map.get(mime_type, '')
				
				# If not found in the map, try to extract from MIME type
				if not real_ext and '/' in mime_type:
					potential_ext = mime_type.split('/')[-1]
					if potential_ext in ['jpeg', 'jpg', 'png', 'gif', 'webp', 'heic', 'heif', 'mp4', 'mov', 'mpeg', 'avi']:
						real_ext = 'jpg' if potential_ext == 'jpeg' else potential_ext
				
				return real_ext, mime_type
		except Exception as e:
			logger.debug(f"Error detecting file type for {file_path}: {str(e)}")
		
		# If the type could not be determined, return the extension from the filename
		file_ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
		return file_ext, mimetypes.guess_type(file_path)[0] or ''

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
		
		# Determine the real file type, not just the extension
		real_ext, mime_type = ExifToolService.detect_file_type(file_path)
		file_ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
		
		# Check if the extension doesn't match the actual file type
		if real_ext and real_ext != file_ext:
			# Skip jpg/jpeg cases as they are essentially the same format
			if (real_ext.lower() == 'jpg' and file_ext.lower() == 'jpeg') or (real_ext.lower() == 'jpeg' and file_ext.lower() == 'jpg'):
				pass  # Don't show warning or fix extension
			else:
				logger.info(f"File {file_path} has extension '{file_ext}' but is actually a '{real_ext}' file")
				
				# Fix file extension for all file types with incorrect extensions
				fixed_path = ExifToolService.fix_file_extension(file_path)
				
				# If the path has changed (i.e., a copy with the correct extension was created)
				if fixed_path != file_path and os.path.exists(fixed_path):
					logger.info(f"Using file with correct extension: {fixed_path}")
					# Use the new path for further processing
					file_path = fixed_path
					# Update the extension and file type for further processing
					file_ext = os.path.splitext(fixed_path)[1][1:].lower()
					real_ext = file_ext  # Now the extension matches the real type
		
		# Create a copy of arguments for modification depending on the file type
		adjusted_args = metadata_args.copy()
		
		# Special handling for different file types based on the real type
		if real_ext == 'jpg' or 'jpeg' in mime_type or file_ext.lower() == 'jpg':
			# For JPEG files (including those that were renamed)
			# Use standard arguments for JPEG files
			adjusted_args.append('-ignoreMinorErrors')
		elif real_ext == 'heic' or 'heic' in mime_type:
			# For actual HEIC files, use a safer set of arguments
			# Remove GPS coordinates which often cause problems
			adjusted_args = [arg for arg in adjusted_args if not arg.startswith('-GPS')]
			# Add special flags for HEIC files
			adjusted_args.append('-ignoreMinorErrors')
		elif real_ext in ['png', 'gif'] or any(x in mime_type for x in ['png', 'gif']):
			# For PNG and GIF files, keep only the basic date metadata
			adjusted_args = [arg for arg in adjusted_args if arg.startswith('-DateTime') or arg.startswith('-Create') or arg.startswith('-Modify')]
			# Add additional flags for PNG files
			adjusted_args.append('-ignoreMinorErrors')
			adjusted_args.append('-overwrite_original_in_place')
		elif real_ext.lower() in ['mpg', 'mpeg'] or 'mpeg' in mime_type:
			# Special handling for MPG files which are particularly problematic
			# Keep only date metadata and add special flags
			adjusted_args = [arg for arg in adjusted_args if arg.startswith('-DateTime') or arg.startswith('-Create') or arg.startswith('-Modify')]
			adjusted_args.append('-ignoreMinorErrors')
			adjusted_args.append('-m')
			adjusted_args.append('-overwrite_original_in_place')
		elif real_ext.lower() in ['avi'] or 'avi' in mime_type:
			# Special handling for AVI files
			# Keep only date metadata and add special flags
			adjusted_args = [arg for arg in adjusted_args if arg.startswith('-DateTime') or arg.startswith('-Create') or arg.startswith('-Modify')]
			adjusted_args.append('-ignoreMinorErrors')
			adjusted_args.append('-m')
			adjusted_args.append('-overwrite_original_in_place')
		elif real_ext.lower() in ['aae'] or file_ext.lower() == 'aae':
			# For AAE files (Apple edit information), only update basic metadata
			adjusted_args = [arg for arg in adjusted_args if arg.startswith('-DateTime') or arg.startswith('-Create') or arg.startswith('-Modify')]
			adjusted_args.append('-ignoreMinorErrors')
		elif real_ext in ['mp4', 'mov', 'wmv'] or any(x in mime_type for x in ['video', 'quicktime']):
			# For other video files, use special flags
			adjusted_args.append('-ignoreMinorErrors')
			adjusted_args.append('-use MWG')
		
		try:
			cmd = ['exiftool']
			cmd.extend(adjusted_args)
			
			# Overwrite original file
			cmd.extend(['-overwrite_original', file_path])
			
			if dry_run:
				logger.info(f"[DRY RUN] Would execute: {' '.join(cmd)}")
				return True
			
			# Use subprocess.run without check=True to handle errors ourselves
			try:
				result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
			except subprocess.TimeoutExpired:
				logger.warning(f"Command timed out for {file_path}, trying with simplified arguments")
				# If timeout occurs, try with only date metadata
				date_args = [arg for arg in adjusted_args if arg.startswith('-DateTime') or arg.startswith('-Create') or arg.startswith('-Modify')]
				if date_args:
					cmd = ['exiftool']
					cmd.extend(date_args)
					cmd.extend(['-ignoreMinorErrors', '-m', '-overwrite_original', file_path])
					try:
						result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
					except Exception:
						logger.error(f"Failed to update metadata for {file_path} after timeout")
						return False
				else:
					logger.error(f"Failed to update metadata for {file_path} after timeout")
					return False
			
			if result.returncode == 0:
				logger.info(f"Successfully updated metadata for {file_path}")
				return True
			else:
				# If the first attempt failed, try with dates only
				if result.returncode != 0 and not dry_run:
					logger.warning(f"First attempt failed for {file_path}, trying with dates only")
					
					# Keep only date-related arguments
					date_args = [arg for arg in adjusted_args if arg.startswith('-DateTime') or arg.startswith('-Create') or arg.startswith('-Modify')]
					
					if date_args:
						cmd = ['exiftool']
						cmd.extend(date_args)
						cmd.extend(['-ignoreMinorErrors', '-overwrite_original', file_path])
						
						try:
							try:
								result2 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
							except subprocess.TimeoutExpired:
								logger.error(f"Second attempt timed out for {file_path}")
								return False
							if result2.returncode == 0:
								logger.info(f"Partially updated date metadata for {file_path}, but full metadata update failed")
								# Return False because we only applied partial metadata
								return False
							else:
								# If that didn't work either, try to force the file type
								if 'Not a valid HEIC' in result2.stderr.decode() and real_ext == 'jpg':
									logger.warning(f"Trying to force JPEG format for {file_path}")
									cmd = ['exiftool']
									cmd.extend(date_args)
									cmd.extend(['-FileType=JPEG', '-ignoreMinorErrors', '-overwrite_original', file_path])
									
									try:
										try:
											result3 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
										except subprocess.TimeoutExpired:
											logger.error(f"Third attempt timed out for {file_path}")
											return False
										if result3.returncode == 0:
											logger.info(f"Partially updated metadata with forced JPEG format for {file_path}, but full metadata update failed")
											# Return False because we only applied partial metadata
											return False
										else:
											logger.error(f"Failed to update metadata even with forced JPEG format for {file_path}: {result3.stderr.decode()}")
									except Exception as e3:
										logger.error(f"Error in third attempt for {file_path}: {str(e3)}")
								else:
									logger.error(f"Failed to update even date metadata for {file_path}: {result2.stderr.decode()}")
						except Exception as e2:
							logger.error(f"Error in second attempt for {file_path}: {str(e2)}")
				
				logger.error(f"Failed to update metadata for {file_path}: {result.stderr.decode()}")
				return False
		except Exception as e:
			logger.error(f"Error applying metadata to {file_path}: {str(e)}")
			return False
	
	@staticmethod
	def apply_specialized_metadata_for_problematic_files(file_path: str) -> bool:
		"""
		Apply specialized metadata handling for problematic file types (MPG, AVI, etc.)
		This is a last-resort method for files that failed normal metadata application
		
		Args:
			file_path: Path to the file
			
		Returns:
			True if successful, False otherwise
		"""
		try:
			# Get file extension
			file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
			
			# Determine file creation time from filesystem
			try:
				creation_time = os.path.getctime(file_path)
				modification_time = os.path.getmtime(file_path)
				
				# Format dates for exiftool
				from datetime import datetime
				date_format = "%Y:%m:%d %H:%M:%S"
				creation_date = datetime.fromtimestamp(creation_time).strftime(date_format)
				modify_date = datetime.fromtimestamp(modification_time).strftime(date_format)
			except Exception as e:
				logger.warning(f"Could not get file times for {file_path}: {str(e)}")
				return False
			
			# Create basic command with only date metadata
			cmd = [
				'exiftool',
				f'-CreateDate={creation_date}',
				f'-ModifyDate={modify_date}',
				f'-DateTimeOriginal={creation_date}',
				'-ignoreMinorErrors',
				'-m',  # Ignore minor errors and warnings
				'-overwrite_original',
				file_path
			]
			
			# Special handling for specific file types
			if file_ext in ['mpg', 'mpeg']:
				# For MPG files, use a more direct approach
				cmd.insert(1, '-P')  # Preserve file modification date
				cmd.insert(1, '-F')  # Force writing even if tags already exist
			elif file_ext in ['avi']:
				# For AVI files
				cmd.insert(1, '-F')  # Force writing
			elif file_ext in ['png']:
				# For PNG files
				cmd.insert(1, '-F')  # Force writing
			
			# Execute command with timeout
			try:
				result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
				if result.returncode == 0:
					logger.info(f"Successfully applied specialized metadata to {file_path}")
					return True
				else:
					logger.error(f"Failed to apply specialized metadata to {file_path}: {result.stderr}")
					return False
			except subprocess.TimeoutExpired:
				logger.error(f"Specialized metadata command timed out for {file_path}")
				return False
			
		except Exception as e:
			logger.error(f"Error in specialized metadata handling for {file_path}: {str(e)}")
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
		if not os.path.exists(file_path):
			logger.error(f"File not found: {file_path}")
			return None
		
		try:
			# Use -j for JSON output and -G for grouping tags by their family
			cmd = ['exiftool', '-j', '-G', file_path]
			result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
			
			if result.returncode != 0:
				logger.error(f"Failed to get metadata for {file_path}: {result.stderr}")
				return None
			
			# Parse JSON output
			import json
			try:
				data = json.loads(result.stdout)
				if data and isinstance(data, list) and len(data) > 0:
					return data[0]  # Return the first item in the array
				else:
					logger.warning(f"No metadata found in JSON response for {file_path}")
					return {}
			except json.JSONDecodeError as json_err:
				logger.error(f"Error parsing JSON metadata for {file_path}: {str(json_err)}")
				return None
		except Exception as e:
			logger.error(f"Error getting metadata from {file_path}: {str(e)}")
			return None
