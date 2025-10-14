# app/services/audio_cache_service.py

import hashlib
from typing import Dict, Any, Optional, Tuple, List
import redis.asyncio as redis
import time
import asyncio
import zlib

from ..core.logging import logger
from ..core.redis_client import get_redis
from ..core.settings import settings
from .audio_metrics import AudioMetrics


class AudioCacheService:
    """
    Servicio para cachear respuestas de audio generadas por TTS.
    Utiliza Redis para almacenar las respuestas y permite configurar TTL
    por tipo de contenido.
    """

    # Prefijo para claves de caché en Redis
    CACHE_PREFIX = "audio_cache:"

    # TTL en segundos para diferentes tipos de respuestas (24 horas por defecto)
    DEFAULT_TTL = 86400

    # TTLs específicos por tipo de contenido
    TTL_CONFIG = {
        "welcome_message": 7 * 86400,  # 7 días para mensajes de bienvenida
        "common_responses": 3 * 86400,  # 3 días para respuestas comunes
        "error_messages": 7 * 86400,  # 7 días para mensajes de error
        # Los demás tipos usarán DEFAULT_TTL
    }

    # Tamaño máximo por archivo para almacenar en caché (2MB por defecto)
    MAX_CACHE_SIZE_BYTES = 2 * 1024 * 1024

    # TTL por defecto (24 horas)
    DEFAULT_CACHE_TTL = 86400

    def __init__(self):
        self._redis = None
        self._enabled = settings.audio_cache_enabled
        self._default_ttl = settings.audio_cache_ttl_seconds or self.DEFAULT_CACHE_TTL
        self._max_cache_size_mb = settings.audio_cache_max_size_mb
        self._cleanup_threshold_percent = 95  # Limpiar al alcanzar 95% del límite
        self._target_size_percent = 80  # Reducir al 80% del límite después de limpiar
        self._cleanup_lock = asyncio.Lock()  # Lock para evitar limpiezas simultáneas

        # Configuración de compresión
        self._compression_enabled = settings.audio_cache_compression_enabled
        self._compression_threshold_kb = settings.audio_cache_compression_threshold_kb
        self._compression_level = min(9, max(1, settings.audio_cache_compression_level))  # Asegurar rango 1-9

    async def _get_redis(self) -> redis.Redis:
        """Obtener conexión a Redis de forma lazy."""
        if not self._redis:
            self._redis = await get_redis()
        return self._redis

    def _get_cache_key(self, text: str, voice: str = "default") -> str:
        """
        Genera una clave única para la caché basada en el texto y la voz.

        Args:
            text: Texto a sintetizar
            voice: Identificador de voz (default si no se especifica)

        Returns:
            Clave única para Redis
        """
        # Generar hash basado en texto + voz para evitar colisiones
        content_hash = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
        return f"{self.CACHE_PREFIX}{content_hash}"

    def _get_ttl(self, content_type: Optional[str] = None) -> int:
        """
        Obtiene el TTL adecuado según el tipo de contenido.

        Args:
            content_type: Tipo de contenido para determinar TTL

        Returns:
            TTL en segundos
        """
        if content_type and content_type in self.TTL_CONFIG:
            return self.TTL_CONFIG[content_type]
        if self._default_ttl is not None:
            return self._default_ttl
        return self.DEFAULT_CACHE_TTL

    def _should_compress(self, data: bytes) -> bool:
        """
        Determina si los datos deben comprimirse según su tamaño y configuración.

        Args:
            data: Datos binarios a evaluar

        Returns:
            True si se debe comprimir, False en caso contrario
        """
        if not self._compression_enabled:
            return False

        # Comprimir si supera el umbral configurado
        return len(data) > (self._compression_threshold_kb * 1024)

    def _compress_data(self, data: bytes) -> bytes:
        """
        Comprime datos binarios usando zlib y los codifica en base64.

        Args:
            data: Datos binarios originales

        Returns:
            Datos comprimidos
        """
        if not data:
            return data

        try:
            # Comprimir con nivel configurable
            compressed = zlib.compress(data, level=self._compression_level)

            # Crear formato para almacenar
            # Prefijo "c:" indica que es contenido comprimido
            result = b"c:" + compressed

            compression_ratio = len(data) / len(compressed)
            bytes_saved = len(data) - len(compressed)

            # Registrar métricas
            AudioMetrics.record_compression_operation("compress")
            AudioMetrics.record_operation_with_value("audio_cache_compression_bytes_saved", bytes_saved)
            AudioMetrics.record_operation_with_value("audio_cache_compression_ratio", compression_ratio)

            logger.debug(f"Datos comprimidos: {len(data)} → {len(compressed)} bytes (ratio: {compression_ratio:.2f}x)")

            return result
        except Exception as e:
            logger.warning(f"Error comprimiendo datos: {e}")
            AudioMetrics.record_compression_operation("compress_error")
            # En caso de error, devolver datos originales
            return data

    def _decompress_data(self, data: bytes) -> bytes:
        """
        Descomprime datos si están en formato comprimido.

        Args:
            data: Datos potencialmente comprimidos

        Returns:
            Datos descomprimidos
        """
        if not data or len(data) < 3:
            return data

        try:
            # Verificar si los datos están comprimidos (prefijo "c:")
            if data[:2] == b"c:":
                start_time = time.time()

                # Extraer datos comprimidos
                compressed_data = data[2:]

                # Descomprimir
                decompressed = zlib.decompress(compressed_data)

                # Registrar métricas
                AudioMetrics.record_compression_operation("decompress")
                decompress_time = time.time() - start_time
                AudioMetrics.record_operation_duration("audio_decompression", decompress_time)

                expansion_ratio = len(decompressed) / len(compressed_data)
                logger.debug(
                    f"Datos descomprimidos: {len(compressed_data)} → {len(decompressed)} bytes (ratio: {expansion_ratio:.2f}x)"
                )

                return decompressed
            else:
                # No está comprimido
                return data
        except Exception as e:
            logger.warning(f"Error descomprimiendo datos: {e}")
            AudioMetrics.record_compression_operation("decompress_error")
            # En caso de error, devolver datos originales
            return data

    async def get(
        self, text: str, voice: str = "default", content_type: Optional[str] = None
    ) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Obtiene audio cacheado si existe.

        Args:
            text: Texto para el que se generó el audio
            voice: Identificador de voz
            content_type: Tipo de contenido

        Returns:
            Tupla (datos_audio, metadata) o None si no está en caché
        """
        if not self._enabled:
            return None

        try:
            start_time = time.time()
            redis_client = await self._get_redis()
            cache_key = self._get_cache_key(text, voice)

            # Obtener audio cacheado
            cached_data = await redis_client.get(cache_key)

            if cached_data:
                # Recuperar metadata
                metadata_key = f"{cache_key}:meta"
                metadata_raw = await redis_client.hgetall(metadata_key)
                metadata = {}

                # Convertir bytes a valores Python
                for k, v in metadata_raw.items():
                    key = k.decode() if isinstance(k, bytes) else k
                    val = v.decode() if isinstance(v, bytes) and not key.endswith("_bytes") else v

                    # Convertir valores numéricos
                    try:
                        if isinstance(val, str) and val.isdigit():
                            val = int(val)
                        elif isinstance(val, str) and val.replace(".", "", 1).isdigit():
                            val = float(val)
                    except Exception:
                        pass

                    metadata[key] = val

                # Descomprimir si es necesario
                is_compressed = metadata.get("compressed", False)

                if is_compressed or cached_data[:2] == b"c:":  # Verificación doble
                    decompressed_data = self._decompress_data(cached_data)

                    # Registrar métricas de descompresión
                    compression_ratio = len(decompressed_data) / len(cached_data) if cached_data else 1
                    logger.debug(
                        f"Audio descomprimido: {len(cached_data)} → {len(decompressed_data)} bytes (ratio: {compression_ratio:.2f}x)"
                    )
                    AudioMetrics.record_operation("audio_cache", "decompression")

                    cached_data = decompressed_data

                # Actualizar métricas
                access_time = time.time() - start_time
                AudioMetrics.record_operation_duration("audio_cache_hit", access_time)
                AudioMetrics.record_operation("audio_cache", "hit")

                # Actualizar metadata de uso
                redis_client.hincrby(metadata_key, "hits", 1)  # No await - operación fire and forget

                logger.debug(f"Audio cache hit for text: '{text[:30]}...' ({len(cached_data)} bytes)")
                return (cached_data, metadata)
            else:
                # Cache miss
                AudioMetrics.record_operation("audio_cache", "miss")
                return None

        except Exception as e:
            logger.warning(f"Error accessing audio cache: {e}")
            AudioMetrics.record_error("audio_cache_access_error")
            return None

    async def set(
        self,
        text: str,
        audio_data: bytes,
        voice: str = "default",
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Almacena audio en caché.

        Args:
            text: Texto para el que se generó el audio
            audio_data: Datos binarios del audio
            voice: Identificador de voz
            content_type: Tipo de contenido para determinar TTL
            metadata: Información adicional sobre el audio

        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        if not self._enabled:
            return False

        # No cachear archivos muy grandes
        if len(audio_data) > self.MAX_CACHE_SIZE_BYTES:
            logger.debug(f"Audio too large for cache: {len(audio_data)} bytes")
            AudioMetrics.record_operation("audio_cache", "too_large")
            return False

        try:
            start_time = time.time()
            redis_client = await self._get_redis()
            cache_key = self._get_cache_key(text, voice)
            ttl = self._get_ttl(content_type)

            # Determinar si se debe comprimir
            original_size = len(audio_data)
            should_compress = self._should_compress(audio_data)
            final_data = audio_data

            # Comprimir si es necesario
            if should_compress:
                compressed_data = self._compress_data(audio_data)

                # Solo usar compresión si reduce el tamaño
                if len(compressed_data) < len(audio_data):
                    final_data = compressed_data
                    is_compressed = True
                    compression_ratio = len(audio_data) / len(compressed_data)
                    logger.debug(
                        f"Audio comprimido: {len(audio_data)} → {len(compressed_data)} bytes (ratio: {compression_ratio:.2f}x)"
                    )
                    AudioMetrics.record_operation("audio_cache", "compression")
                else:
                    is_compressed = False
                    logger.debug("No se usó compresión (no reduce el tamaño)")
            else:
                is_compressed = False

            # Guardar audio
            await redis_client.set(cache_key, final_data, ex=ttl)

            # Guardar metadata
            if metadata is None:
                metadata = {}

            # Añadir metadata básica
            metadata.update(
                {
                    "timestamp": time.time(),
                    "size_bytes": len(final_data),
                    "original_size": original_size,
                    "ttl": ttl,
                    "content_type": content_type or "general",
                    "voice": voice,
                    "hits": 0,
                    "text_length": len(text),
                    "compressed": is_compressed,
                }
            )

            if is_compressed:
                metadata["compression_ratio"] = round(compression_ratio, 2)

            # Guardar metadata con el mismo TTL
            metadata_key = f"{cache_key}:meta"
            if metadata:
                for key, value in metadata.items():
                    redis_client.hset(metadata_key, key, value)
                await redis_client.expire(metadata_key, ttl)

            # Actualizar métricas
            set_time = time.time() - start_time
            AudioMetrics.record_operation_duration("audio_cache_set", set_time)
            AudioMetrics.record_operation("audio_cache", "set")
            AudioMetrics.record_file_size("cached_audio", len(final_data))

            # Log específico según compresión
            if is_compressed:
                logger.debug(
                    f"Cached compressed audio for text: '{text[:30]}...' ({len(final_data)} bytes, ratio: {compression_ratio:.2f}x, TTL: {ttl}s)"
                )
            else:
                logger.debug(f"Cached audio for text: '{text[:30]}...' ({len(final_data)} bytes, TTL: {ttl}s)")

            # Verificar y limpiar caché si es necesario (sin esperar)
            asyncio.create_task(self._check_and_cleanup_cache(len(final_data)))

            return True

        except Exception as e:
            logger.warning(f"Error setting audio cache: {e}")
            AudioMetrics.record_error("audio_cache_set_error")
            return False

    async def _check_and_cleanup_cache(self, new_entry_size: int = 0) -> Dict[str, Any]:
        """
        Verifica si la caché excede el tamaño máximo configurado y limpia si es necesario.
        Implementa una estrategia de limpieza que combina antigüedad, uso y tamaño.

        Args:
            new_entry_size: Tamaño de la nueva entrada añadida (para prever si excederá el límite)

        Returns:
            Diccionario con resultados de la operación de limpieza
        """
        if not self._enabled or self._max_cache_size_mb <= 0:
            return {"status": "disabled"}

        # Evitar múltiples limpiezas simultáneas
        if not self._cleanup_lock.locked():
            # No esperamos que se adquiera el lock para permitir operaciones async
            if not await self._cleanup_lock.acquire():
                return {"status": "locked"}

            try:
                # Obtener estadísticas actuales de la caché
                stats = await self.get_cache_stats()
                current_size_mb = stats.get("total_size_mb", 0)
                max_size_mb = self._max_cache_size_mb

                # Calcular umbral de limpieza y tamaño objetivo
                cleanup_threshold_mb = max_size_mb * (self._cleanup_threshold_percent / 100.0)
                target_size_mb = max_size_mb * (self._target_size_percent / 100.0)

                # Nueva entrada empujaría el tamaño por encima del umbral?
                new_entry_size_mb = new_entry_size / (1024 * 1024)
                projected_size_mb = current_size_mb + new_entry_size_mb

                if projected_size_mb <= cleanup_threshold_mb:
                    logger.debug(f"Cache size ok: {current_size_mb:.2f}MB < {cleanup_threshold_mb:.2f}MB threshold")
                    return {"status": "not_needed"}

                # Calcular cuánto espacio necesitamos liberar
                to_free_mb = projected_size_mb - target_size_mb
                to_free_bytes = int(to_free_mb * 1024 * 1024)

                if to_free_mb <= 0:
                    return {"status": "not_needed"}

                logger.info(
                    f"Iniciando limpieza automática de caché: {current_size_mb:.2f}MB → {target_size_mb:.2f}MB (liberando {to_free_mb:.2f}MB)"
                )

                # Obtener todas las entradas con su metadata para evaluación
                entries = await self._get_all_cache_entries_with_score()

                # Ordenar entradas por puntuación (menor = mayor prioridad para eliminación)
                entries.sort(key=lambda e: e["score"])

                freed_bytes = 0
                deleted_count = 0

                redis_client = await self._get_redis()

                # Eliminar entradas hasta alcanzar el espacio necesario
                for entry in entries:
                    if freed_bytes >= to_free_bytes:
                        break

                    # Eliminar la entrada y su metadata
                    await redis_client.delete(entry["key"])
                    await redis_client.delete(f"{entry['key']}:meta")

                    freed_bytes += entry["size_bytes"]
                    deleted_count += 1

                    logger.debug(
                        f"Eliminada entrada de caché: {entry['key']} ({entry['size_bytes'] / 1024:.2f}KB, score: {entry['score']:.2f})"
                    )

                # Registrar métricas
                AudioMetrics.record_operation("audio_cache", "auto_cleanup")
                AudioMetrics.record_operation_with_value("audio_cache_cleanup_freed_mb", freed_bytes / (1024 * 1024))
                AudioMetrics.record_operation_with_value("audio_cache_cleanup_entries_removed", deleted_count)

                result = {
                    "status": "completed",
                    "freed_mb": round(freed_bytes / (1024 * 1024), 2),
                    "entries_removed": deleted_count,
                    "previous_size_mb": current_size_mb,
                    "new_size_mb": current_size_mb - (freed_bytes / (1024 * 1024)),
                }

                logger.info(
                    f"Limpieza automática completada: {deleted_count} entradas eliminadas, {result['freed_mb']:.2f}MB liberados"
                )
                return result

            except Exception as e:
                logger.error(f"Error durante limpieza automática de caché: {e}")
                AudioMetrics.record_error("audio_cache_cleanup_error")
                return {"status": "error", "error": str(e)}

            finally:
                self._cleanup_lock.release()

        return {"status": "already_running"}

    async def _get_all_cache_entries_with_score(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las entradas de la caché con su metadata y calcula una puntuación
        para determinar qué entradas eliminar primero.

        La puntuación combina:
        - Antigüedad (más viejo = más propenso a ser eliminado)
        - Frecuencia de uso (menos usado = más propenso a ser eliminado)
        - Tamaño (más grande = más propenso a ser eliminado, pero solo como desempate)

        Returns:
            Lista de entradas con su puntuación
        """
        redis_client = await self._get_redis()
        entries = []
        now = time.time()
        cursor = 0

        # Obtener todas las claves de audio (sin metadata)
        all_keys = []
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match=f"{self.CACHE_PREFIX}*", count=100)

            # Filtrar solo claves principales (no metadata)
            audio_keys = [
                k.decode() if isinstance(k, bytes) else k for k in keys if b":meta" not in k and ":meta" not in str(k)
            ]
            all_keys.extend(audio_keys)

            if cursor == 0:
                break

        # Procesar en lotes para evitar operaciones individuales
        batch_size = 50
        for i in range(0, len(all_keys), batch_size):
            batch_keys = all_keys[i : i + batch_size]

            # Obtener tamaños en pipeline
            size_pipe = redis_client.pipeline()
            for key in batch_keys:
                size_pipe.strlen(key)
            sizes = await size_pipe.execute()

            # Obtener metadata en pipeline
            meta_pipe = redis_client.pipeline()
            for key in batch_keys:
                meta_pipe.hgetall(f"{key}:meta")
            metadata_list = await meta_pipe.execute()

            # Procesar resultados
            for j, key in enumerate(batch_keys):
                size = sizes[j] if j < len(sizes) else 0
                metadata = metadata_list[j] if j < len(metadata_list) else {}

                # Convertir bytes a strings en metadata
                converted_metadata = {}
                for mk, mv in metadata.items():
                    k = mk.decode() if isinstance(mk, bytes) else mk
                    v = mv.decode() if isinstance(mv, bytes) and not k.endswith("_bytes") else mv

                    # Convertir valores numéricos
                    try:
                        if isinstance(v, str) and v.isdigit():
                            v = int(v)
                        elif isinstance(v, str) and v.replace(".", "", 1).isdigit():
                            v = float(v)
                    except Exception:
                        pass

                    converted_metadata[k] = v

                # Extraer valores relevantes
                timestamp = float(converted_metadata.get("timestamp", now - 86400))  # Default: 1 día atrás
                hits = int(converted_metadata.get("hits", 0))
                content_type = converted_metadata.get("content_type", "unknown")

                # Calcular factores de puntuación
                age_factor = (now - timestamp) / 86400  # Edad en días
                usage_factor = max(1, 10 - hits) / 10  # Inverso del uso normalizado (0.1-1.0)

                # Contenido común debería tener menor prioridad para eliminar
                type_factor = 0.5 if content_type in ["welcome_message", "common_responses"] else 1.0

                # Calcular puntuación (mayor = menos prioritario para eliminar)
                # Fórmula: más antiguo + menos usado + (tamaño como desempate)
                score = (age_factor * 0.7) + (usage_factor * 0.3) * type_factor

                # Añadir a la lista
                entries.append(
                    {
                        "key": key,
                        "size_bytes": size,
                        "timestamp": timestamp,
                        "hits": hits,
                        "content_type": content_type,
                        "score": score,
                    }
                )

        return entries

    async def invalidate(self, text: str, voice: str = "default") -> bool:
        """
        Invalida una entrada específica de la caché.

        Args:
            text: Texto para el que se generó el audio
            voice: Identificador de voz

        Returns:
            True si se invalidó correctamente, False en caso contrario
        """
        if not self._enabled:
            return False

        try:
            redis_client = await self._get_redis()
            cache_key = self._get_cache_key(text, voice)

            # Eliminar entrada y metadata
            await redis_client.delete(cache_key)
            await redis_client.delete(f"{cache_key}:meta")

            AudioMetrics.record_operation("audio_cache", "invalidate")
            return True

        except Exception as e:
            logger.warning(f"Error invalidating audio cache: {e}")
            AudioMetrics.record_error("audio_cache_invalidate_error")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso de la caché de audio.

        Returns:
            Diccionario con estadísticas
        """
        if not self._enabled:
            return {"enabled": False}

        try:
            redis_client = await self._get_redis()

            # Contar entradas de caché
            cursor = 0
            count = 0
            total_size = 0

            # Escanear con patrón para contar entradas y tamaño
            while True:
                cursor, keys = await redis_client.scan(cursor=cursor, match=f"{self.CACHE_PREFIX}*", count=100)

                # Filtrar sólo claves de audio (sin metadata)
                audio_keys = [k for k in keys if b":meta" not in k]
                count += len(audio_keys)

                # Calcular tamaño de las entradas encontradas
                if audio_keys:
                    # Obtener tamaños en pipeline para optimizar
                    pipe = redis_client.pipeline()
                    for key in audio_keys:
                        pipe.strlen(key)
                    sizes = await pipe.execute()
                    total_size += sum(s for s in sizes if s)

                if cursor == 0:
                    break

            # Actualizar métricas de caché
            AudioMetrics.update_cache_size(count)
            AudioMetrics.update_cache_memory(total_size)

            # Calcular porcentaje de uso respecto al límite configurado
            max_size_bytes = self._max_cache_size_mb * 1024 * 1024
            usage_percent = (total_size / max_size_bytes) * 100 if max_size_bytes > 0 else 0

            # Calcular umbrales
            cleanup_threshold_mb = self._max_cache_size_mb * (self._cleanup_threshold_percent / 100.0)
            target_size_mb = self._max_cache_size_mb * (self._target_size_percent / 100.0)

            # Recopilar información sobre compresión
            compressed_count = 0
            compressed_size = 0
            original_size = 0

            # Escanear claves de metadata para encontrar entradas comprimidas
            cursor = 0
            while True:
                cursor, meta_keys = await redis_client.scan(
                    cursor=cursor, match=f"{self.CACHE_PREFIX}*:meta", count=100
                )

                if meta_keys:
                    pipe = redis_client.pipeline()
                    for key in meta_keys:
                        pipe.hget(key, "compressed")
                        pipe.hget(key, "size_bytes")
                        pipe.hget(key, "original_size")

                    results = await pipe.execute()
                    for i in range(0, len(results), 3):
                        if i + 2 < len(results):
                            is_compressed = results[i] == b"True" or results[i] == b"1" or results[i]
                            if is_compressed:
                                compressed_count += 1
                                size_bytes = int(results[i + 1]) if results[i + 1] else 0
                                orig_bytes = int(results[i + 2]) if results[i + 2] else 0
                                compressed_size += size_bytes
                                original_size += orig_bytes

                if cursor == 0:
                    break

            # Calcular estadísticas de compresión
            space_saved = original_size - compressed_size
            space_saved_mb = space_saved / (1024 * 1024) if space_saved > 0 else 0
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 0

            return {
                "enabled": True,
                "entries_count": count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size > 0 else 0,
                "max_cache_size_mb": self._max_cache_size_mb,
                "usage_percent": round(usage_percent, 2),
                "max_entry_size_mb": round(self.MAX_CACHE_SIZE_BYTES / (1024 * 1024), 2),
                "cleanup_threshold_mb": round(cleanup_threshold_mb, 2),
                "target_size_after_cleanup_mb": round(target_size_mb, 2),
                "auto_cleanup": {
                    "enabled": self._enabled and self._max_cache_size_mb > 0,
                    "threshold_percent": self._cleanup_threshold_percent,
                    "target_percent": self._target_size_percent,
                },
                "compression": {
                    "enabled": self._compression_enabled,
                    "threshold_kb": self._compression_threshold_kb,
                    "compression_level": self._compression_level,
                    "compressed_entries": compressed_count,
                    "compressed_size_mb": round(compressed_size / (1024 * 1024), 2) if compressed_size > 0 else 0,
                    "original_size_mb": round(original_size / (1024 * 1024), 2) if original_size > 0 else 0,
                    "space_saved_mb": round(space_saved_mb, 2),
                    "compression_ratio": round(compression_ratio, 2) if compression_ratio > 0 else 0,
                },
            }

        except Exception as e:
            logger.warning(f"Error getting audio cache stats: {e}")
            return {"enabled": self._enabled, "error": str(e)}

    async def clear_cache(self) -> int:
        """
        Limpia toda la caché de audio.

        Returns:
            Número de entradas eliminadas
        """
        if not self._enabled:
            return 0

        try:
            redis_client = await self._get_redis()

            # Contar entradas eliminadas
            deleted_count = 0
            cursor = 0

            # Escanear con patrón para evitar cargar todas las claves a la vez
            while True:
                cursor, keys = await redis_client.scan(cursor=cursor, match=f"{self.CACHE_PREFIX}*", count=100)

                if keys:
                    deleted = await redis_client.delete(*keys)
                    deleted_count += deleted

                if cursor == 0:
                    break

            AudioMetrics.record_operation("audio_cache", "clear")
            logger.info(f"Audio cache cleared: {deleted_count} entries removed")
            return deleted_count

        except Exception as e:
            logger.error(f"Error clearing audio cache: {e}")
            AudioMetrics.record_error("audio_cache_clear_error")
            return 0


# Instancia singleton
_audio_cache_service = None


async def get_audio_cache_service() -> AudioCacheService:
    """
    Obtiene instancia singleton del servicio de caché de audio.
    """
    global _audio_cache_service
    if _audio_cache_service is None:
        _audio_cache_service = AudioCacheService()
    return _audio_cache_service
