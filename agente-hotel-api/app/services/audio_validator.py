# Audio Validation Middleware

import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Any
from ..exceptions.audio_exceptions import AudioValidationError
from ..core.logging import logger


class AudioValidator:
    """
    Validador de archivos de audio para asegurar formato y tamaño adecuados
    """
    
    # Tipos MIME soportados
    SUPPORTED_MIME_TYPES = {
        'audio/ogg',
        'audio/mpeg',
        'audio/mp4',
        'audio/wav',
        'audio/webm',
        'audio/amr'
    }
    
    # Extensiones soportadas
    SUPPORTED_EXTENSIONS = {
        '.ogg', '.mp3', '.mp4', '.wav', '.webm', '.amr', '.aac'
    }
    
    # Tamaño máximo de archivo (25MB)
    MAX_FILE_SIZE = 25 * 1024 * 1024
    
    # Duración máxima en segundos (10 minutos)
    MAX_DURATION = 600
    
    def __init__(self):
        self.validation_rules = {
            'mime_type': self._validate_mime_type,
            'file_extension': self._validate_file_extension,
            'file_size': self._validate_file_size,
            'file_exists': self._validate_file_exists
        }
    
    async def validate_audio_url(self, url: str) -> Dict[str, Any]:
        """
        Valida una URL de audio antes de la descarga
        
        :param url: URL del archivo de audio
        :return: Diccionario con resultado de validación
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Validar formato de URL
            if not url or not isinstance(url, str):
                validation_result['valid'] = False
                validation_result['errors'].append("Invalid URL format")
                return validation_result
            
            # Validar esquema de URL
            if not url.startswith(('http://', 'https://')):
                validation_result['valid'] = False
                validation_result['errors'].append("URL must use HTTP or HTTPS protocol")
                return validation_result
            
            # Intentar detectar extensión desde URL
            path = Path(url.split('?')[0])  # Remover parámetros de query
            if path.suffix and path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                validation_result['warnings'].append(f"Potentially unsupported file extension: {path.suffix}")
            
            logger.debug(f"URL validation passed for: {url[:50]}...")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"URL validation error: {str(e)}")
            logger.error(f"Error validating audio URL: {e}")
        
        return validation_result
    
    async def validate_audio_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Valida un archivo de audio local
        
        :param file_path: Ruta al archivo de audio
        :return: Diccionario con resultado de validación
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'metadata': {}
        }
        
        try:
            # Ejecutar todas las reglas de validación
            for rule_name, rule_func in self.validation_rules.items():
                try:
                    rule_result = await rule_func(file_path)
                    if not rule_result['valid']:
                        validation_result['valid'] = False
                        validation_result['errors'].extend(rule_result['errors'])
                    validation_result['warnings'].extend(rule_result.get('warnings', []))
                    validation_result['metadata'].update(rule_result.get('metadata', {}))
                except Exception as e:
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Validation rule '{rule_name}' failed: {str(e)}")
                    logger.error(f"Error in validation rule {rule_name}: {e}")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"File validation error: {str(e)}")
            logger.error(f"Error validating audio file: {e}")
        
        return validation_result
    
    async def _validate_file_exists(self, file_path: Path) -> Dict[str, Any]:
        """Valida que el archivo existe"""
        result = {'valid': True, 'errors': [], 'metadata': {}}
        
        if not file_path.exists():
            result['valid'] = False
            result['errors'].append(f"File does not exist: {file_path}")
        elif not file_path.is_file():
            result['valid'] = False
            result['errors'].append(f"Path is not a file: {file_path}")
        
        return result
    
    async def _validate_file_size(self, file_path: Path) -> Dict[str, Any]:
        """Valida el tamaño del archivo"""
        result = {'valid': True, 'errors': [], 'metadata': {}}
        
        try:
            file_size = file_path.stat().st_size
            result['metadata']['file_size'] = file_size
            
            if file_size == 0:
                result['valid'] = False
                result['errors'].append("File is empty")
            elif file_size > self.MAX_FILE_SIZE:
                result['valid'] = False
                result['errors'].append(f"File too large: {file_size} bytes (max: {self.MAX_FILE_SIZE})")
            
        except OSError as e:
            result['valid'] = False
            result['errors'].append(f"Cannot access file stats: {str(e)}")
        
        return result
    
    async def _validate_mime_type(self, file_path: Path) -> Dict[str, Any]:
        """Valida el tipo MIME del archivo"""
        result = {'valid': True, 'errors': [], 'warnings': [], 'metadata': {}}
        
        try:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            result['metadata']['mime_type'] = mime_type
            
            if mime_type and mime_type not in self.SUPPORTED_MIME_TYPES:
                result['warnings'].append(f"Potentially unsupported MIME type: {mime_type}")
            
        except Exception as e:
            result['warnings'].append(f"Could not determine MIME type: {str(e)}")
        
        return result
    
    async def _validate_file_extension(self, file_path: Path) -> Dict[str, Any]:
        """Valida la extensión del archivo"""
        result = {'valid': True, 'errors': [], 'warnings': [], 'metadata': {}}
        
        extension = file_path.suffix.lower()
        result['metadata']['extension'] = extension
        
        if extension not in self.SUPPORTED_EXTENSIONS:
            result['warnings'].append(f"Potentially unsupported file extension: {extension}")
        
        return result
    
    def raise_if_invalid(self, validation_result: Dict[str, Any], context: str = ""):
        """
        Lanza AudioValidationError si la validación falló
        
        :param validation_result: Resultado de la validación
        :param context: Contexto adicional para el error
        """
        if not validation_result['valid']:
            error_message = f"Audio validation failed{f' ({context})' if context else ''}"
            if validation_result['errors']:
                error_message += f": {'; '.join(validation_result['errors'])}"
            
            raise AudioValidationError(error_message)