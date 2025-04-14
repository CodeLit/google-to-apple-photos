"""
Models for photo metadata
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class PhotoMetadata:
	"""Represents metadata extracted from Google Takeout JSON files"""
	
	# Original filename
	filename: str
	
	# Date and time when the photo was taken
	date_taken: datetime
	
	# Optional fields
	title: Optional[str] = None
	description: Optional[str] = None
	
	# Location data
	latitude: Optional[float] = None
	longitude: Optional[float] = None
	
	# Original JSON data
	raw_data: Optional[Dict[str, Any]] = None
	
	@classmethod
	def from_json(cls, json_data: Dict[str, Any]) -> 'PhotoMetadata':
		"""
		Create a PhotoMetadata object from Google Takeout JSON data
		
		Args:
			json_data: Dictionary containing the JSON data
			
		Returns:
			PhotoMetadata object
		"""
		# Get required fields
		filename = json_data.get('title', '')
		
		# Get photo taken time
		photo_taken_time = None
		if 'photoTakenTime' in json_data and 'timestamp' in json_data['photoTakenTime']:
			timestamp = int(json_data['photoTakenTime']['timestamp'])
			photo_taken_time = datetime.fromtimestamp(timestamp)
		else:
			# Fallback to creation time if photo taken time is not available
			if 'creationTime' in json_data and 'timestamp' in json_data['creationTime']:
				timestamp = int(json_data['creationTime']['timestamp'])
				photo_taken_time = datetime.fromtimestamp(timestamp)
			else:
				# Use current time as a last resort
				photo_taken_time = datetime.now()
		
		# Get optional fields
		description = json_data.get('description', '')
		
		# Get location data
		latitude = None
		longitude = None
		if 'geoData' in json_data:
			geo_data = json_data['geoData']
			if 'latitude' in geo_data and geo_data['latitude'] != 0:
				latitude = geo_data['latitude']
			if 'longitude' in geo_data and geo_data['longitude'] != 0:
				longitude = geo_data['longitude']
		
		return cls(
			filename=filename,
			date_taken=photo_taken_time,
			title=filename,
			description=description,
			latitude=latitude,
			longitude=longitude,
			raw_data=json_data
		)
	
	def to_exiftool_args(self) -> List[str]:
		"""
		Convert metadata to exiftool arguments
		
		Returns:
			List of arguments for exiftool
		"""
		args = []
		
		# Format date as YYYY:MM:DD HH:MM:SS
		date_str = self.date_taken.strftime('%Y:%m:%d %H:%M:%S')
		
		# Add date fields
		args.extend([
			f'-DateTimeOriginal={date_str}',
			f'-CreateDate={date_str}',
			f'-ModifyDate={date_str}'
		])
		
		# Add title if available
		if self.title:
			args.append(f'-Title={self.title}')
		
		# Add description if available
		if self.description:
			args.append(f'-Description={self.description}')
			args.append(f'-ImageDescription={self.description}')
		
		# Add location data if available
		if self.latitude is not None and self.longitude is not None:
			args.append(f'-GPSLatitude={self.latitude}')
			args.append(f'-GPSLongitude={self.longitude}')
		
		return args
