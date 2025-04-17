"""
Service for interacting with Apple Photos application
"""
import os
import subprocess
import logging
import json
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)

class PhotosAppService:
	"""Service for interacting with Apple Photos application"""
	
	# AppleScript templates for interacting with Photos app
	ADD_PHOTO_SCRIPT = """
	on unixDate(datetime)
		set command to "date -j -f '%A, %B %e, %Y at %I:%M:%S %p' '" & datetime & "'"
		set command to command & " +%s"

		set theUnixDate to do shell script command
		return theUnixDate
	end unixDate
	on run {image_path, image_filename, image_timestamp, image_size}
		tell application "Photos"
			set images to search for image_filename
			repeat with img in images
				set myFilename to filename of img
				set myTimestamp to my unixDate(get date of img)
				set mySize to size of img
				if image_filename is equal to myFilename and mySize is equal to (image_size as integer)
					if image_timestamp is equal to "" or image_timestamp is equal to myTimestamp
						return (get id of img)
					end if
				end if
			end repeat

			set posixFile to (image_path as POSIX file)
			import posixFile with skip check duplicates
		end tell
		return ""
	end run
	"""
	
	ADD_PHOTO_TO_ALBUM_SCRIPT = """
	on unixDate(datetime)
		set command to "date -j -f '%A, %B %e, %Y at %I:%M:%S %p' '" & datetime & "'"
		set command to command & " +%s"

		set theUnixDate to do shell script command
		return theUnixDate
	end unixDate
	on run {albumName, image_path, image_filename, image_timestamp, image_size}
		tell application "Photos"
			if not (exists album named albumName) then
				make new album named albumName
			end if

			set images to search for image_filename
			repeat with img in images
				set myFilename to filename of img
				set myTimestamp to my unixDate(get date of img)
				set mySize to size of img
				if image_filename is equal to myFilename and mySize is equal to (image_size as integer)
					if image_timestamp is equal to "" or image_timestamp is equal to myTimestamp
						set imgList to {img}
						add imgList to album named albumName
						return (get id of img)
					end if
				end if
			end repeat

			set posixFile to (image_path as POSIX file)
			import posixFile into album named albumName with skip check duplicates
		end tell
		return ""
	end run
	"""
	
	PROGRESS_FILE = "photos_import_progress.json"
	
	@staticmethod
	def import_photo(image_path: str, timestamp: str = "") -> str:
		"""
		Import a photo into Apple Photos
		
		Args:
			image_path: Path to the image file
			timestamp: Unix timestamp (optional)
			
		Returns:
			Photo ID if already exists, empty string if imported
		"""
		if not os.path.exists(image_path):
			logger.error(f"File not found: {image_path}")
			return ""
			
		image_filename = os.path.basename(image_path)
		image_size = os.path.getsize(image_path)
		
		args = [image_path, image_filename, timestamp, str(image_size)]
		process = subprocess.Popen(
			["osascript", "-"] + args, 
			stdin=subprocess.PIPE, 
			stdout=subprocess.PIPE, 
			stderr=subprocess.PIPE
		)
		
		stdout, stderr = process.communicate(PhotosAppService.ADD_PHOTO_SCRIPT.encode("utf-8"))
		
		if stderr:
			logger.error(f"Error importing photo: {stderr.decode('utf-8')}")
			
		result = stdout.decode("utf-8").strip()
		if result:
			logger.info(f"Photo already exists in library: {image_filename}")
		else:
			logger.info(f"Imported photo: {image_filename}")
			
		return result
	
	@staticmethod
	def import_photo_to_album(album_name: str, image_path: str, timestamp: str = "") -> str:
		"""
		Import a photo into Apple Photos and add it to an album
		
		Args:
			album_name: Name of the album
			image_path: Path to the image file
			timestamp: Unix timestamp (optional)
			
		Returns:
			Photo ID if already exists, empty string if imported
		"""
		if not os.path.exists(image_path):
			logger.error(f"File not found: {image_path}")
			return ""
			
		image_filename = os.path.basename(image_path)
		image_size = os.path.getsize(image_path)
		
		args = [album_name, image_path, image_filename, timestamp, str(image_size)]
		process = subprocess.Popen(
			["osascript", "-"] + args, 
			stdin=subprocess.PIPE, 
			stdout=subprocess.PIPE, 
			stderr=subprocess.PIPE
		)
		
		stdout, stderr = process.communicate(PhotosAppService.ADD_PHOTO_TO_ALBUM_SCRIPT.encode("utf-8"))
		
		if stderr:
			logger.error(f"Error importing photo to album: {stderr.decode('utf-8')}")
			
		result = stdout.decode("utf-8").strip()
		if result:
			logger.info(f"Photo {image_filename} already exists in album: {album_name}")
		else:
			logger.info(f"Imported photo {image_filename} to album: {album_name}")
			
		return result
	
	@staticmethod
	def load_progress() -> Dict:
		"""
		Load progress from the progress file
		
		Returns:
			Dictionary with progress information
		"""
		if os.path.exists(PhotosAppService.PROGRESS_FILE):
			try:
				with open(PhotosAppService.PROGRESS_FILE, 'r') as f:
					return json.load(f)
			except Exception as e:
				logger.error(f"Error loading progress file: {str(e)}")
		return {}
	
	@staticmethod
	def save_progress(progress: Dict) -> None:
		"""
		Save progress to the progress file
		
		Args:
			progress: Dictionary with progress information
		"""
		try:
			with open(PhotosAppService.PROGRESS_FILE, 'w') as f:
				json.dump(progress, f, indent=2)
		except Exception as e:
			logger.error(f"Error saving progress file: {str(e)}")
	
	@staticmethod
	def extract_album_metadata(directory: str) -> List[Tuple[str, str]]:
		"""
		Extract album metadata from Google Takeout directory
		
		Args:
			directory: Path to the Google Takeout directory
			
		Returns:
			List of tuples (album_path, album_name)
		"""
		albums = []
		for root, dirs, files in os.walk(directory):
			for file in files:
				if file == "metadata.json":
					try:
						with open(os.path.join(root, file), 'r') as f:
							data = json.load(f)
							if "title" in data:
								albums.append((root, data["title"]))
					except Exception as e:
						logger.error(f"Error reading album metadata: {str(e)}")
		return albums
	
	@staticmethod
	def get_photo_timestamp(photo_path: str) -> str:
		"""
		Get timestamp from photo metadata JSON file
		
		Args:
			photo_path: Path to the photo
			
		Returns:
			Timestamp string or empty string if not found
		"""
		# Handle both direct JSON path and photo path
		if photo_path.endswith('.json'):
			json_path = photo_path
		else:
			json_path = photo_path + ".json"
		
		if os.path.exists(json_path):
			try:
				with open(json_path, 'r') as f:
					data = json.load(f)
					if "photoTakenTime" in data and "timestamp" in data["photoTakenTime"]:
						return data["photoTakenTime"]["timestamp"]
			except Exception as e:
				logger.error(f"Error reading photo metadata: {str(e)}")
		return ""
	
	@staticmethod
	def import_photos_from_directory(directory: str, with_albums: bool = True) -> Tuple[int, int]:
		"""
		Import photos from a directory into Apple Photos
		
		Args:
			directory: Path to the directory containing photos
			with_albums: Whether to organize photos into albums
			
		Returns:
			Tuple (imported_count, skipped_count)
		"""
		imported_count = 0
		skipped_count = 0
		
		# Load progress
		progress = PhotosAppService.load_progress()
		
		# Process albums first if requested
		if with_albums:
			albums = PhotosAppService.extract_album_metadata(directory)
			logger.info(f"Found {len(albums)} albums")
			
			for album_path, album_name in albums:
				if album_path in progress:
					logger.info(f"Skipping already processed album: {album_name}")
					continue
					
				logger.info(f"Processing album: {album_name}")
				album_imported = 0
				album_skipped = 0
				
				# Get all photos in the album
				for root, dirs, files in os.walk(album_path):
					for file in files:
						if file.startswith(".") or file.endswith(".json"):
							continue
							
						photo_path = os.path.join(root, file)
						timestamp = PhotosAppService.get_photo_timestamp(photo_path)
						
						result = PhotosAppService.import_photo_to_album(album_name, photo_path, timestamp)
						if result:
							album_skipped += 1
							skipped_count += 1
						else:
							album_imported += 1
							imported_count += 1
				
				logger.info(f"Album {album_name}: Imported {album_imported}, Skipped {album_skipped}")
				progress[album_path] = True
				PhotosAppService.save_progress(progress)
		
		# Process loose photos (not in albums or all photos if albums not requested)
		for root, dirs, files in os.walk(directory):
			# Skip if this directory is an album and we've already processed it
			if with_albums and root in progress:
				continue
				
			for file in files:
				if file.startswith(".") or file.endswith(".json") or file == "archive_browser.html":
					continue
					
				photo_path = os.path.join(root, file)
				timestamp = PhotosAppService.get_photo_timestamp(photo_path)
				
				result = PhotosAppService.import_photo(photo_path, timestamp)
				if result:
					skipped_count += 1
				else:
					imported_count += 1
		
		return imported_count, skipped_count
