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
		Исправляет расширение файла, если оно не соответствует реальному типу файла
		
		Args:
			file_path: Путь к файлу
			
		Returns:
			Путь к файлу с правильным расширением (может быть тем же самым)
		"""
		if not os.path.exists(file_path):
			logger.error(f"File not found: {file_path}")
			return file_path
		
		real_ext, mime_type = ExifToolService.detect_file_type(file_path)
		if not real_ext:
			logger.debug(f"Could not determine real file type for {file_path}")
			return file_path
		
		# Получаем текущее расширение файла
		file_ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
		
		# Если расширение уже соответствует реальному типу файла
		if real_ext.lower() == file_ext.lower():
			return file_path
		
		# Карта корректировок для разных типов файлов
		fix_map = {
			# Фото
			'jpg': ['heic', 'png', 'jpeg', 'jfif', 'webp'],  # JPEG файлы с неправильными расширениями
			'png': ['jpg', 'jpeg', 'heic'],  # PNG файлы с неправильными расширениями
			'heic': ['jpg', 'jpeg', 'png'],  # HEIC файлы с неправильными расширениями
			# Видео
			'mp4': ['mov', 'avi', '3gp'],  # MP4 файлы с неправильными расширениями
			'mov': ['mp4', 'avi', '3gp'],  # MOV файлы с неправильными расширениями
		}
		
		# Проверяем, нужно ли исправлять расширение
		if real_ext in fix_map and file_ext in fix_map.get(real_ext, []):
			# Создаем новое имя файла с правильным расширением
			base_name = os.path.splitext(file_path)[0]
			new_path = f"{base_name}.{real_ext}"
			
			# Проверяем, существует ли уже файл с таким именем
			if os.path.exists(new_path):
				logger.warning(f"File with correct extension already exists: {new_path}")
				# Если файл уже существует, возвращаем его путь
				return new_path
			
			try:
				# Создаем копию файла с правильным расширением
				shutil.copy2(file_path, new_path)
				logger.info(f"Copied {file_path} to {new_path} with correct extension ({file_ext} -> {real_ext})")
				
				# Проверяем, что копия создалась успешно и имеет правильный размер
				if os.path.exists(new_path) and os.path.getsize(new_path) > 0:
					return new_path
				else:
					logger.error(f"Failed to create valid copy with correct extension: {new_path}")
					# Удаляем неудачную копию
					if os.path.exists(new_path):
						try:
							os.remove(new_path)
						except Exception:
							pass
					return file_path
			except Exception as e:
				logger.error(f"Error copying file {file_path} to {new_path}: {str(e)}")
				return file_path
		
		# Если тип файла не требует исправления или не поддерживается
		return file_path

	@staticmethod
	def detect_file_type(file_path: str) -> Tuple[str, str]:
		"""
		Определяет реальный тип файла, независимо от расширения
		
		Args:
			file_path: Путь к файлу
			
		Returns:
			Тюпл (реальное_расширение, mime_type)
		"""
		if not os.path.exists(file_path):
			logger.error(f"File not found: {file_path}")
			return '', ''
		
		# Расширенная карта MIME-типов
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
			# Метод 1: Используем exiftool для определения типа файла
			cmd = ['exiftool', '-FileType', '-s3', file_path]
			result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
			
			if result.returncode == 0 and result.stdout.strip():
				real_ext = result.stdout.strip().lower()
				
				# Получаем MIME тип на основе реального расширения
				mime_type = mimetypes.guess_type(f"file.{real_ext}")[0] or ''
				
				# Проверяем специальные случаи
				if real_ext.lower() == 'jpeg':
					real_ext = 'jpg'
				
				return real_ext, mime_type
			
			# Метод 2: Если exiftool не смог определить тип, используем file command
			cmd = ['file', '--mime-type', '-b', file_path]
			result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
			
			if result.returncode == 0 and result.stdout.strip():
				mime_type = result.stdout.strip()
				
				# Преобразуем MIME тип в расширение
				real_ext = ext_map.get(mime_type, '')
				
				# Если не нашли в карте, попробуем извлечь из MIME типа
				if not real_ext and '/' in mime_type:
					potential_ext = mime_type.split('/')[-1]
					if potential_ext in ['jpeg', 'jpg', 'png', 'gif', 'webp', 'heic', 'heif', 'mp4', 'mov', 'mpeg', 'avi']:
						real_ext = 'jpg' if potential_ext == 'jpeg' else potential_ext
				
				return real_ext, mime_type
		except Exception as e:
			logger.debug(f"Error detecting file type for {file_path}: {str(e)}")
		
		# Если не удалось определить тип, возвращаем расширение из имени файла
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
		
		# Определяем реальный тип файла, а не только расширение
		real_ext, mime_type = ExifToolService.detect_file_type(file_path)
		file_ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
		
		# Проверяем, если расширение не соответствует реальному типу файла
		if real_ext and real_ext != file_ext:
			logger.info(f"File {file_path} has extension '{file_ext}' but is actually a '{real_ext}' file")
			
			# Исправляем расширение файла для всех типов файлов с неправильным расширением
			fixed_path = ExifToolService.fix_file_extension(file_path)
			
			# Если путь изменился (т.е. была создана копия с правильным расширением)
			if fixed_path != file_path and os.path.exists(fixed_path):
				logger.info(f"Using file with correct extension: {fixed_path}")
				# Используем новый путь для дальнейшей обработки
				file_path = fixed_path
				# Обновляем расширение и тип файла для дальнейшей обработки
				file_ext = os.path.splitext(fixed_path)[1][1:].lower()
				real_ext = file_ext  # Теперь расширение соответствует реальному типу
		
		# Создаем копию аргументов для модификации в зависимости от типа файла
		adjusted_args = metadata_args.copy()
		
		# Специальная обработка для разных типов файлов на основе реального типа
		if real_ext == 'jpg' or 'jpeg' in mime_type or file_ext.lower() == 'jpg':
			# Для JPEG файлов (включая те, которые были переименованы)
			# Для JPEG файлов используем стандартные аргументы
			adjusted_args.append('-ignoreMinorErrors')
		elif real_ext == 'heic' or 'heic' in mime_type:
			# Для настоящих HEIC файлов используем более безопасный набор аргументов
			# Убираем GPS координаты, которые часто вызывают проблемы
			adjusted_args = [arg for arg in adjusted_args if not arg.startswith('-GPS')]
			# Добавляем специальные флаги для HEIC файлов
			adjusted_args.append('-ignoreMinorErrors')
		elif real_ext in ['png', 'gif'] or any(x in mime_type for x in ['png', 'gif']):
			# Для PNG и GIF файлов оставляем только основные метаданные даты
			adjusted_args = [arg for arg in adjusted_args if arg.startswith('-DateTime') or arg.startswith('-Create') or arg.startswith('-Modify')]
		elif real_ext in ['mpg', 'avi', 'mp4', 'mov', 'wmv'] or any(x in mime_type for x in ['video', 'mpeg', 'quicktime']):
			# Для видео файлов используем специальные флаги
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
			
			# Используем subprocess.run без check=True, чтобы обработать ошибки самостоятельно
			result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			
			if result.returncode == 0:
				logger.info(f"Successfully updated metadata for {file_path}")
				return True
			else:
				# Если первая попытка не удалась, попробуем только с датами
				if result.returncode != 0 and not dry_run:
					logger.warning(f"First attempt failed for {file_path}, trying with dates only")
					
					# Оставляем только аргументы с датами
					date_args = [arg for arg in adjusted_args if arg.startswith('-DateTime') or arg.startswith('-Create') or arg.startswith('-Modify')]
					
					if date_args:
						cmd = ['exiftool']
						cmd.extend(date_args)
						cmd.extend(['-ignoreMinorErrors', '-overwrite_original', file_path])
						
						try:
							result2 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
							if result2.returncode == 0:
								logger.info(f"Successfully updated date metadata for {file_path}")
								return True
							else:
								# Если и это не сработало, попробуем принудительно указать тип файла
								if 'Not a valid HEIC' in result2.stderr.decode() and real_ext == 'jpg':
									logger.warning(f"Trying to force JPEG format for {file_path}")
									cmd = ['exiftool']
									cmd.extend(date_args)
									cmd.extend(['-FileType=JPEG', '-ignoreMinorErrors', '-overwrite_original', file_path])
									
									try:
										result3 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
										if result3.returncode == 0:
											logger.info(f"Successfully updated metadata with forced JPEG format for {file_path}")
											return True
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
