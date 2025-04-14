"""
Service for handling metadata operations
"""
import os
import json
import logging
import csv
import re
import concurrent.futures
from typing import Optional, Dict, List, Tuple, Set
from datetime import datetime

from src.models.metadata import PhotoMetadata
from src.utils.file_utils import get_base_filename, find_matching_file
from src.utils.image_utils import find_matching_file_by_hash, is_media_file, find_duplicates, compute_hash_for_file

logger = logging.getLogger(__name__)

# Create a separate logger for processed files
processed_logger = logging.getLogger('processed_files')
processed_logger.setLevel(logging.INFO)
processed_logger.propagate = False  # Don't propagate to parent loggers

# Create a separate logger for failed updates
failed_updates_logger = logging.getLogger('failed_updates')
failed_updates_logger.setLevel(logging.INFO)
failed_updates_logger.propagate = False  # Don't propagate to parent loggers


class MetadataService:
	"""Service for handling metadata operations"""
	
	@staticmethod
	def parse_json_metadata(json_file: str) -> Optional[PhotoMetadata]:
		"""
		Parse Google Takeout JSON metadata file and extract relevant information
		
		Args:
			json_file: Path to the JSON metadata file
			
		Returns:
			PhotoMetadata object or None if parsing failed
		"""
		try:
			with open(json_file, 'r', encoding='utf-8') as f:
				data = json.load(f)
			
			return PhotoMetadata.from_json(data)
		except Exception as e:
			logger.error(f"Error parsing JSON file {json_file}: {str(e)}")
			return None
	
	@staticmethod
	def setup_processed_files_logger(log_file: str = 'processed_files.log', failed_updates_log: str = 'failed_updates.log'):
		"""Set up separate loggers for processed files and failed updates"""
		# Set up processed files logger
		if not processed_logger.handlers:
			file_handler = logging.FileHandler(log_file, mode='w')
			file_handler.setFormatter(logging.Formatter('%(message)s'))
			processed_logger.addHandler(file_handler)
			
			# Write CSV header
			processed_logger.info("source_file,target_file,match_method,similarity,date_modified")
		
		# Set up failed updates logger
		if not failed_updates_logger.handlers:
			failed_file_handler = logging.FileHandler(failed_updates_log, mode='w')
			failed_file_handler.setFormatter(logging.Formatter('%(message)s'))
			failed_updates_logger.addHandler(failed_file_handler)
			
			# Write CSV header
			failed_updates_logger.info("file_path,error_message,timestamp")

	@staticmethod
	def log_processed_file(source_file: str, target_file: str, match_method: str, similarity: float = 0.0):
		"""Log a processed file pair to the processed files log"""
		try:
			date_modified = datetime.fromtimestamp(os.path.getmtime(target_file)).strftime('%Y-%m-%d %H:%M:%S')
			processed_logger.info(f"{source_file},{target_file},{match_method},{similarity:.4f},{date_modified}")
		except Exception as e:
			logger.error(f"Error logging processed file: {str(e)}")
			
	@staticmethod
	def log_failed_update(file_path: str, error_message: str):
		"""Log a failed metadata update to the failed updates log"""
		try:
			timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
			failed_updates_logger.info(f"{file_path},{error_message},{timestamp}")
		except Exception as e:
			logger.error(f"Error logging failed update: {str(e)}")

	@staticmethod
	def find_metadata_pairs(old_dir: str, new_dir: str, use_hash_matching: bool = True, 
						   similarity_threshold: float = 0.98, duplicates_log: str = 'duplicates.log') -> List[Tuple[str, str, PhotoMetadata]]:
		"""
		Find pairs of files between old and new directories with their metadata
		
		Args:
			old_dir: Directory with Google Takeout files
			new_dir: Directory with Apple Photos exports
			use_hash_matching: Whether to use image hash matching for more accurate results
			similarity_threshold: Threshold for considering images as matches (0.0 to 1.0)
			
		Returns:
			List of tuples (json_file, new_file, metadata)
		"""
		# Set up the processed files logger
		MetadataService.setup_processed_files_logger()
		
		pairs = []
		processed_count = 0
		json_count = 0
		match_count = 0
		hash_match_count = 0
		name_match_count = 0
		
		# Create optimized data structures for faster matching
		logger.info(f"Caching files in {new_dir} for faster matching...")
		new_files_dict = {}  # For name-based matching
		new_files_list = []  # For hash-based matching
		
		try:
			# Walk through the new directory once and build both data structures
			for root, _, files in os.walk(new_dir):
				for file in files:
					file_path = os.path.join(root, file)
					if is_media_file(file_path):
						# Add to list for hash matching
						new_files_list.append(file_path)
						
						# Add to dictionary for name matching
						base_name = os.path.splitext(file)[0].lower()
						new_files_dict[base_name] = file_path
						
						# Also add with (1), (2) etc. removed for better matching
						import re
						clean_name = re.sub(r'\s*\(\d+\)$', '', base_name)
						if clean_name != base_name:
							new_files_dict[clean_name] = file_path
			
			logger.info(f"Found {len(new_files_list)} media files in the new directory")
			
			# Precompute hashes for all files in the new directory if using hash matching
			if use_hash_matching:
				logger.info("Precomputing hashes for files in the new directory...")
				batch_size = 500
				for i in range(0, len(new_files_list), batch_size):
					batch = new_files_list[i:i+batch_size]
					
					# Process batch in parallel
					with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
						hash_futures = {}
						for target_file in batch:
							hash_futures[executor.submit(compute_hash_for_file, target_file)] = target_file
						
						for future in concurrent.futures.as_completed(hash_futures):
							try:
								future.result()  # Just compute and cache the hash
							except Exception:
								pass
					
					if (i + batch_size) % 2000 == 0 or (i + batch_size) >= len(new_files_list):
						logger.info(f"Precomputed hashes for {min(i + batch_size, len(new_files_list))} of {len(new_files_list)} files")
		
		except (PermissionError, FileNotFoundError) as e:
			logger.error(f"Error accessing directory {new_dir}: {str(e)}")
			return pairs
		
		# Find and log duplicates in the new directory
		if use_hash_matching:
			logger.info(f"Checking for duplicates in {new_dir}...")
			duplicates = find_duplicates(new_dir, similarity_threshold, duplicates_log)
			if duplicates:
				dup_count = sum(len(dups) for dups in duplicates.values())
				logger.info(f"Found {dup_count} duplicate files in {len(duplicates)} groups")
				
				# Write duplicates to a CSV file
				try:
					with open(duplicates_log, 'w', newline='') as f:
						writer = csv.writer(f)
						writer.writerow(['original', 'duplicate'])
						for original, dups in duplicates.items():
							for dup in dups:
								writer.writerow([original, dup])
				except Exception as e:
					logger.error(f"Error writing duplicates to CSV: {str(e)}")
			else:
				logger.info("No duplicates found")
		
		# Walk through the old directory
		for root, _, files in os.walk(old_dir):
			for file in files:
				processed_count += 1
				
				# Log progress every 100 files
				if processed_count % 100 == 0:
					logger.info(f"Processed {processed_count} files, found {json_count} JSON files with {match_count} matches")
				
				# Only process JSON metadata files
				if file.endswith('.json') and ('.supplemental-metadata' in file or '.supplemental-meta' in file):
					json_count += 1
					json_file = os.path.join(root, file)
					
					try:
						# Parse the JSON file
						metadata = MetadataService.parse_json_metadata(json_file)
						if not metadata:
							continue
						
						# Get the base filename
						base_name = get_base_filename(metadata.filename)
						
						# Try to find the corresponding media file in the old directory
						media_file = None
						possible_media_file = json_file.replace('.supplemental-metadata.json', '').replace('.supplemental-meta.json', '')
						if os.path.exists(possible_media_file) and is_media_file(possible_media_file):
							media_file = possible_media_file
						
						matching_file = None
						similarity = 0.0
						match_method = 'none'
						
						# First try name matching (fastest)
						base_name_lower = base_name.lower()
						if base_name_lower in new_files_dict:
							matching_file = new_files_dict[base_name_lower]
							name_match_count += 1
							match_method = 'name'
							similarity = 1.0
						# Then try hash matching if enabled and we have the media file
						elif use_hash_matching and media_file:
							matching_file = find_matching_file_by_hash(media_file, new_dir, similarity_threshold, new_files_list)
							if matching_file:
								hash_match_count += 1
								match_method = 'hash'
								similarity = similarity_threshold  # We don't have the exact similarity here
						
						# If hash matching failed or is disabled, try name matching
						if not matching_file:
							matching_file = find_matching_file(base_name, new_dir)
							if matching_file:
								name_match_count += 1
								match_method = 'name'
						
						if matching_file:
							match_count += 1
							pairs.append((json_file, matching_file, metadata))
							
							# Log the processed file
							MetadataService.log_processed_file(json_file, matching_file, match_method, similarity)
						else:
							# Only log warnings for files with reasonable filenames
							if len(base_name) > 3 and not base_name.startswith('.'): 
								logger.warning(f"No matching file found for {base_name}")
					except Exception as e:
						logger.error(f"Error processing {json_file}: {str(e)}")
		
		logger.info(f"Finished processing. Found {match_count} matches out of {json_count} JSON files")
		logger.info(f"Match methods: {hash_match_count} by hash, {name_match_count} by name")
		return pairs
