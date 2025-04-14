"""
Service for handling metadata operations
"""
import os
import json
import logging
from typing import Optional, Dict, List, Tuple

from src.models.metadata import PhotoMetadata
from src.utils.file_utils import get_base_filename, find_matching_file

logger = logging.getLogger(__name__)


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
	def find_metadata_pairs(old_dir: str, new_dir: str) -> List[Tuple[str, str, PhotoMetadata]]:
		"""
		Find pairs of files between old and new directories with their metadata
		
		Args:
			old_dir: Directory with Google Takeout files
			new_dir: Directory with Apple Photos exports
			
		Returns:
			List of tuples (json_file, new_file, metadata)
		"""
		pairs = []
		processed_count = 0
		json_count = 0
		match_count = 0
		
		# First, cache all files in the new directory for faster lookups
		logger.info(f"Caching files in {new_dir} for faster matching...")
		new_files = []
		try:
			new_files = os.listdir(new_dir)
			logger.info(f"Found {len(new_files)} files in the new directory")
		except (PermissionError, FileNotFoundError) as e:
			logger.error(f"Error accessing directory {new_dir}: {str(e)}")
			return pairs
		
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
						
						# Find matching file in new directory
						matching_file = find_matching_file(base_name, new_dir)
						if matching_file:
							match_count += 1
							pairs.append((json_file, matching_file, metadata))
						else:
							# Only log warnings for files with reasonable filenames
							if len(base_name) > 3 and not base_name.startswith('.'): 
								logger.warning(f"No matching file found for {base_name}")
					except Exception as e:
						logger.error(f"Error processing {json_file}: {str(e)}")
		
		logger.info(f"Finished processing. Found {match_count} matches out of {json_count} JSON files")
		return pairs
