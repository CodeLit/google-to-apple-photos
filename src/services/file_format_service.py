"""
Service for handling file format operations like conversion and extension correction
"""
import os
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

class FileFormatService:
    """Service for handling file format operations"""
    
    @staticmethod
    def detect_file_format(file_path: str) -> Optional[str]:
        """
        Detect the actual file format using exiftool
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected file format or None if detection failed
        """
        try:
            cmd = ['exiftool', '-FileType', '-s3', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0 and result.stdout.strip():
                file_type = result.stdout.strip().lower()
                # Normalize some common formats
                if file_type == 'jpeg':
                    return 'jpg'
                return file_type
            return None
        except Exception as e:
            logger.error(f"Error detecting file format for {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def is_heic(file_path: str) -> bool:
        """
        Check if a file is in HEIC format
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file is in HEIC format, False otherwise
        """
        try:
            detected_format = FileFormatService.detect_file_format(file_path)
            return detected_format == 'heic'
        except Exception as e:
            logger.error(f"Error checking if file is HEIC: {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def convert_heic_to_jpg(file_path: str, remove_original: bool = True) -> Optional[str]:
        """
        Convert a HEIC file to JPG
        
        Args:
            file_path: Path to the HEIC file
            remove_original: Whether to remove the original HEIC file
            
        Returns:
            Path to the converted JPG file or None if conversion failed
        """
        if not FileFormatService.is_heic(file_path):
            logger.warning(f"File is not HEIC: {file_path}")
            return None
        
        try:
            # Get the output path
            dirname = os.path.dirname(file_path)
            basename = os.path.basename(file_path)
            name_without_ext = os.path.splitext(basename)[0]
            jpg_path = os.path.join(dirname, f"{name_without_ext}.jpg")
            
            # Convert using sips (macOS) or magick (ImageMagick)
            if os.path.exists('/usr/bin/sips'):
                # macOS built-in tool
                cmd = ['sips', '-s', 'format', 'jpeg', file_path, '--out', jpg_path]
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                success = result.returncode == 0
            else:
                # Try ImageMagick
                try:
                    cmd = ['magick', 'convert', file_path, jpg_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    success = result.returncode == 0
                except FileNotFoundError:
                    # If ImageMagick is not installed, try exiftool
                    cmd = ['exiftool', '-b', '-PreviewImage', file_path, '-o', jpg_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    success = result.returncode == 0
            
            if success and os.path.exists(jpg_path):
                logger.info(f"Converted HEIC to JPG: {file_path} -> {jpg_path}")
                
                # Copy metadata from HEIC to JPG
                from src.services.exiftool_service import ExifToolService
                ExifToolService.copy_metadata(file_path, jpg_path)
                
                # Remove original if requested
                if remove_original:
                    os.remove(file_path)
                    logger.info(f"Removed original HEIC file: {file_path}")
                
                return jpg_path
            else:
                logger.error(f"Failed to convert HEIC to JPG: {file_path}")
                if os.path.exists(jpg_path):
                    os.remove(jpg_path)  # Clean up partial file
                return None
        except Exception as e:
            logger.error(f"Error converting HEIC to JPG: {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def fix_file_extension(file_path: str) -> Optional[str]:
        """
        Fix incorrect file extension based on actual file content
        
        Args:
            file_path: Path to the file
            
        Returns:
            Path to the renamed file or None if no change was needed or operation failed
        """
        try:
            detected_format = FileFormatService.detect_file_format(file_path)
            if not detected_format:
                logger.warning(f"Could not detect format for {file_path}")
                return None
            
            # Get current extension
            current_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            
            # Check if extension matches detected format
            if current_ext == detected_format or (current_ext == 'jpeg' and detected_format == 'jpg'):
                return None  # No change needed
            
            # Create new path with correct extension
            dirname = os.path.dirname(file_path)
            basename = os.path.basename(file_path)
            name_without_ext = os.path.splitext(basename)[0]
            new_path = os.path.join(dirname, f"{name_without_ext}.{detected_format}")
            
            # Rename the file
            os.rename(file_path, new_path)
            logger.info(f"Fixed file extension: {file_path} -> {new_path}")
            
            return new_path
        except Exception as e:
            logger.error(f"Error fixing file extension for {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def process_file_formats(file_path: str, convert_heic: bool = True, fix_extensions: bool = True) -> Optional[str]:
        """
        Process a file to fix its format and extension
        
        Args:
            file_path: Path to the file
            convert_heic: Whether to convert HEIC files to JPG
            fix_extensions: Whether to fix incorrect file extensions
            
        Returns:
            Path to the processed file or None if processing failed
        """
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return None
        
        result_path = file_path
        
        # Convert HEIC to JPG if requested
        if convert_heic and FileFormatService.is_heic(result_path):
            jpg_path = FileFormatService.convert_heic_to_jpg(result_path)
            if jpg_path:
                result_path = jpg_path
        
        # Fix file extension if requested
        if fix_extensions and os.path.exists(result_path):
            fixed_path = FileFormatService.fix_file_extension(result_path)
            if fixed_path:
                result_path = fixed_path
        
        return result_path