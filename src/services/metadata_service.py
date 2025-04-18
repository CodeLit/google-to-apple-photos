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

from src.models.metadata import PhotoMetadata, Metadata
from src.utils.file_utils import get_base_filename, extract_date_from_filename, is_uuid_filename, are_duplicate_filenames
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
	def extract_metadata_from_json(json_path: str) -> Optional[Metadata]:
		"""
		Extract metadata from a Google Takeout JSON file

		Args:
			json_path: Path to the JSON file

		Returns:
			Metadata object or None if extraction failed
		"""
		if not os.path.exists(json_path):
			logger.error(f"JSON file not found: {json_path}")
			return None

		try:
			# Read the JSON file
			with open(json_path, 'r', encoding='utf-8') as f:
				json_data = json.load(f)

			# Extract metadata fields
			title = json_data.get('title')

			# Extract date taken
			date_taken = None
			photo_taken_time = json_data.get('photoTakenTime')
			if photo_taken_time and 'timestamp' in photo_taken_time:
				timestamp = int(photo_taken_time['timestamp'])
				date_obj = datetime.fromtimestamp(timestamp)
				date_taken = date_obj.strftime('%Y:%m:%d %H:%M:%S')

			# Extract GPS coordinates
			latitude = None
			longitude = None
			geo_data = json_data.get('geoData')
			if geo_data:
				latitude = geo_data.get('latitude')
				longitude = geo_data.get('longitude')

			# Create and return metadata object
			return Metadata(
				title=title,
				date_taken=date_taken,
				latitude=latitude,
				longitude=longitude
			)

		except json.JSONDecodeError:
			logger.error(f"Invalid JSON format in file: {json_path}")
			return None
		except Exception as e:
			logger.error(f"Error extracting metadata from {json_path}: {str(e)}")
			return None

	@staticmethod
	def find_matching_file(json_path: str, target_dir: str) -> Optional[str]:
		"""
		Find a matching file in the target directory for a given JSON metadata file

		Args:
			json_path: Path to the JSON metadata file
			target_dir: Directory to search for matching files

		Returns:
			Path to the matching file or None if no match found
		"""
		if not os.path.exists(json_path):
			logger.error(f"JSON file not found: {json_path}")
			return None

		if not os.path.exists(target_dir):
			logger.error(f"Target directory not found: {target_dir}")
			return None

		try:
			# Get the base filename from the JSON path
			json_filename = os.path.basename(json_path)

			# Handle supplemental metadata files
			if json_filename.endswith('.supplemental-metadata.json'):
				base_name = json_filename.replace('.supplemental-metadata.json', '')
			elif json_filename.endswith('.json'):
				base_name = get_base_filename(json_filename)
			else:
				logger.warning(f"Unexpected JSON filename format: {json_filename}")
				return None

			# Look for exact filename match first
			for file in os.listdir(target_dir):
				if not os.path.isfile(os.path.join(target_dir, file)):
					continue

				# Skip non-media files
				if not is_media_file(file):
					continue

				# Check for exact match
				if get_base_filename(file) == base_name:
					return os.path.join(target_dir, file)

				# Check for duplicate filenames (with suffixes like '(1)')
				if are_duplicate_filenames(get_base_filename(file), base_name):
					return os.path.join(target_dir, file)

			# If no exact match, try image hash matching
			# Extract the original file path from the JSON directory
			orig_dir = os.path.dirname(json_path)
			potential_orig_files = [f for f in os.listdir(orig_dir) 
								if is_media_file(f) and get_base_filename(f) == base_name]

			if potential_orig_files:
				orig_file = os.path.join(orig_dir, potential_orig_files[0])
				matching_file = find_matching_file_by_hash(orig_file, target_dir)
				if matching_file:
					return matching_file

			return None

		except Exception as e:
			logger.error(f"Error finding matching file for {json_path}: {str(e)}")
			return None

	@staticmethod
	def find_metadata_pairs(old_dir: str, new_dir: str) -> List[Tuple[str, str]]:
		"""
		Find pairs of JSON metadata files and their matching media files

		Args:
			old_dir: Directory containing Google Takeout files (JSON metadata and original media)
			new_dir: Directory containing Apple Photos exports to be updated

		Returns:
			List of tuples (json_path, matching_file_path)
		"""
		if not os.path.exists(old_dir):
			logger.error(f"Old directory not found: {old_dir}")
			return []

		if not os.path.exists(new_dir):
			logger.error(f"New directory not found: {new_dir}")
			return []

		try:
			# Find all JSON files in the old directory
			json_files = []
			for root, _, files in os.walk(old_dir):
				for file in files:
					if file.endswith('.json') or file.endswith('.supplemental-metadata.json'):
						json_files.append(os.path.join(root, file))

			logger.info(f"Found {len(json_files)} JSON files in {old_dir}")

			# Cache files in the new directory for faster matching
			logger.info(f"Caching files in {new_dir} for faster matching...")
			new_files = []
			for root, _, files in os.walk(new_dir):
				for file in files:
					if is_media_file(file):
						new_files.append(os.path.join(root, file))

			logger.info(f"Found {len(new_files)} media files in the new directory")

			# Find matching pairs
			pairs = []
			for json_path in json_files:
				matching_file = MetadataService.find_matching_file(json_path, new_dir)
				if matching_file:
					pairs.append((json_path, matching_file))

			logger.info(f"Found {len(pairs)} matching pairs between JSON metadata and media files")
			return pairs

		except Exception as e:
			logger.error(f"Error finding metadata pairs: {str(e)}")
			return []

	@staticmethod
	def extract_metadata_from_filename(file_path: str) -> Optional[PhotoMetadata]:
		"""
		Extract metadata from filename patterns like IMG-YYYYMMDD-WA0012.jpg or 2021-03-07_23-15-52.jpg

		Args:
			file_path: Path to the file

		Returns:
			PhotoMetadata object or None if no pattern match
		"""
		# Try to extract date from filename
		date_info = extract_date_from_filename(file_path)
		if date_info:
			date_str, pattern_desc = date_info

			# Create a datetime object from the date string
			try:
				# Parse the date string (format: YYYY:MM:DD)
				year, month, day = date_str.split(':')

				# Check if this is a pattern with time component
				if "YYYY-MM-DD_HH-MM-SS pattern" in pattern_desc:
					# Extract time from filename
					filename = os.path.basename(file_path)
					time_match = re.search(r'_([0-9]{2})-([0-9]{2})-([0-9]{2})', filename)
					if time_match:
						hour = int(time_match.group(1))
						minute = int(time_match.group(2))
						second = int(time_match.group(3))
						date_taken = datetime(int(year), int(month), int(day), hour, minute, second)
					else:
						# Fallback to noon if time extraction fails
						date_taken = datetime(int(year), int(month), int(day), 12, 0, 0)
				else:
					# For patterns without time, set to noon
					date_taken = datetime(int(year), int(month), int(day), 12, 0, 0)

				# Create metadata object
				filename = os.path.basename(file_path)
				logger.info(f"Extracted date {date_taken} from filename {filename} using {pattern_desc}")

				return PhotoMetadata(
					filename=filename,
					date_taken=date_taken,
					title=filename,
					description=f"Date extracted from filename pattern: {pattern_desc}"
				)
			except Exception as e:
				logger.warning(f"Error creating metadata from filename {file_path}: {str(e)}")

		return None

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
	def find_files_without_metadata(new_dir: str, json_dir: str) -> List[str]:
		"""
		Find files in the new directory that don't have matching JSON metadata

		Args:
			new_dir: Path to the directory with new files
			json_dir: Path to the directory with JSON metadata files

		Returns:
			List of paths to files without metadata
		"""
		files_without_metadata = []
		processed_duplicates = set()  # Track processed duplicate files

		for filename in os.listdir(new_dir):
			file_path = os.path.join(new_dir, filename)
			if os.path.isfile(file_path):
				# Skip if this file has been processed as a duplicate
				if file_path in processed_duplicates:
					continue

				base_filename = get_base_filename(filename)
				json_path = os.path.join(json_dir, f"{filename}.supplemental-metadata.json")

				# Check for direct match first
				if os.path.exists(json_path):
					continue

				# For UUID-style filenames, check if there's a matching JSON with a different extension
				if is_uuid_filename(filename):
					found_match = False
					for json_filename in os.listdir(json_dir):
						if json_filename.endswith(".supplemental-metadata.json"):
							base_json_filename = json_filename.replace(".supplemental-metadata.json", "")
							if are_duplicate_filenames(filename, base_json_filename):
								found_match = True
								break
					if found_match:
						continue

				# Check for duplicate files in the new directory
				duplicate_files = []
				for other_filename in os.listdir(new_dir):
					if other_filename != filename and are_duplicate_filenames(filename, other_filename):
						duplicate_files.append(os.path.join(new_dir, other_filename))

				# If we found duplicates, add them to the processed set
				for dup_file in duplicate_files:
					processed_duplicates.add(dup_file)

				files_without_metadata.append(file_path)

		return files_without_metadata

	@staticmethod
	def setup_processed_files_logger(log_file: str = 'logs/processed_files.log', failed_updates_log: str = 'logs/failed_updates.log'):
		"""Set up separate loggers for processed files and failed updates"""
		# Create logs directory if it doesn't exist
		logs_dir = os.path.dirname(log_file)
		if not os.path.exists(logs_dir):
			os.makedirs(logs_dir)

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
			duplicates_log: Path to the log file for duplicates

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
							matching_file = MetadataService.find_matching_file(json_file, new_dir)
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

	@staticmethod
	def apply_metadata_to_file(json_path: str, target_file: str, dry_run: bool = False) -> bool:
		"""
		Apply metadata from a JSON file to a target file

		Args:
			json_path: Path to the JSON metadata file
			target_file: Path to the target file to update
			dry_run: If True, don't actually modify the file (default: False)

		Returns:
			True if successful, False otherwise
		"""
		from src.services.exiftool_service import ExifToolService

		# Extract metadata from the JSON file
		metadata = MetadataService.extract_metadata_from_json(json_path)
		if not metadata:
			logger.error(f"Failed to extract metadata from {json_path}")
			return False

		# Convert metadata to exiftool arguments
		exif_args = metadata.to_exiftool_args()

		# Apply metadata to the target file
		if ExifToolService.apply_metadata(target_file, exif_args, dry_run):
			logger.info(f"Successfully applied metadata to {target_file}")
			return True
		else:
			logger.error(f"Failed to apply metadata to {target_file}")
			return False

	@staticmethod
	def process_metadata_pairs(pairs: List[Tuple[str, str]], dry_run: bool = False) -> Tuple[int, int]:
		"""
		Process a list of metadata pairs

		Args:
			pairs: List of tuples (json_path, target_file)
			dry_run: If True, don't actually modify any files

		Returns:
			Tuple of (total processed, successful)
		"""
		processed = 0
		successful = 0

		for json_path, target_file in pairs:
			processed += 1

			# Log progress every 10 files
			if processed % 10 == 0:
				logger.info(f"Processed {processed} of {len(pairs)} files, {successful} successful")

			# Apply metadata to the target file
			if dry_run:
				logger.info(f"[DRY RUN] Would apply metadata to {target_file}")
				successful += 1
			elif MetadataService.apply_metadata_to_file(json_path, target_file):
				successful += 1

		logger.info(f"Finished processing {processed} files, {successful} successful")
		return processed, successful

	@staticmethod
	def sync_metadata(old_dir: str, new_dir: str, dry_run: bool = False) -> Tuple[int, int, int]:
		"""
		Synchronize metadata between directories

		Args:
			old_dir: Directory with Google Takeout files
			new_dir: Directory with Apple Photos exports
			dry_run: If True, don't actually modify any files

		Returns:
			Tuple of (total pairs found, total processed, successful)
		"""
		# Find metadata pairs
		pairs = MetadataService.find_metadata_pairs(old_dir, new_dir)

		# Convert pairs to (json_path, target_file) format
		# Handle both 2-element and 3-element tuples
		simple_pairs = []
		for pair in pairs:
			if len(pair) == 2:
				simple_pairs.append(pair)
			elif len(pair) == 3:
				json_path, target_file, _ = pair
				simple_pairs.append((json_path, target_file))

		# Process the pairs
		processed, successful = MetadataService.process_metadata_pairs(simple_pairs, dry_run)

		return len(pairs), processed, successful
