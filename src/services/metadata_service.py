"""
Service for handling metadata operations
"""
import os
import json
import logging
import csv
from typing import Optional, Dict, List, Tuple, Set
from datetime import datetime

from src.models.metadata import PhotoMetadata
from src.utils.file_utils import get_base_filename, find_matching_file
from src.utils.image_utils import find_matching_file_by_hash, is_media_file, find_duplicates

logger = logging.getLogger(__name__)

# Create a separate logger for processed files
processed_logger = logging.getLogger('processed_files')
processed_logger.setLevel(logging.INFO)
processed_logger.propagate = False  # Don't propagate to parent loggers


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
	def setup_processed_files_logger(log_file: str = 'processed_files.log'):
		"""Set up a separate logger for processed files"""
		if not processed_logger.handlers:
			file_handler = logging.FileHandler(log_file, mode='w')
			file_handler.setFormatter(logging.Formatter('%(message)s'))
			processed_logger.addHandler(file_handler)
			
			# Write CSV header
			processed_logger.info("source_file,target_file,match_method,similarity,date_modified")

	@staticmethod
	def log_processed_file(source_file: str, target_file: str, match_method: str, similarity: float = 0.0):
		"""Log a processed file pair to the processed files log"""
		try:
			date_modified = datetime.fromtimestamp(os.path.getmtime(target_file)).strftime('%Y-%m-%d %H:%M:%S')
			processed_logger.info(f"{source_file},{target_file},{match_method},{similarity:.4f},{date_modified}")
		except Exception as e:
			logger.error(f"Error logging processed file: {str(e)}")

	@staticmethod
	def find_metadata_pairs(old_dir: str, new_dir: str, use_hash_matching: bool = True, 
						   similarity_threshold: float = 0.98) -> List[Tuple[str, str, PhotoMetadata]]:
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
		
		# First, cache all files in the new directory for faster lookups
		logger.info(f"Caching files in {new_dir} for faster matching...")
		new_files = []
		try:
			new_files = os.listdir(new_dir)
			logger.info(f"Found {len(new_files)} files in the new directory")
		except (PermissionError, FileNotFoundError) as e:
			logger.error(f"Error accessing directory {new_dir}: {str(e)}")
			return pairs
		
		# Find and log duplicates in the new directory
		if use_hash_matching:
			logger.info(f"Checking for duplicates in {new_dir}...")
			duplicates = find_duplicates(new_dir, similarity_threshold)
			if duplicates:
				dup_count = sum(len(dups) for dups in duplicates.values())
				logger.info(f"Found {dup_count} duplicate files in {len(duplicates)} groups")
				
				# Write duplicates to a CSV file
				try:
					with open('duplicates.log', 'w', newline='') as f:
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
						
						# First try hash matching if enabled and we have the media file
						if use_hash_matching and media_file:
							matching_file = find_matching_file_by_hash(media_file, new_dir, similarity_threshold)
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
