#!/usr/bin/env python3
"""
Script de análisis de Redis Cache para Agente Hotelero IA.

Audita el uso de cache Redis conectándose a la instancia y recopilando métricas:
- Lista todas las keys por patrón (availability:*, session:*, lock:*)
- Calcula hit ratio estimado por tipo de key
- Identifica keys sin TTL (PERSIST)
- Sugiere ajustes de TTL basados en patterns de acceso
- Genera reporte JSON en .playbook/redis_analysis.json

Uso:
    python scripts/analyze_redis_cache.py
    python scripts/analyze_redis_cache.py --host localhost --port 6379
    python scripts/analyze_redis_cache.py --output custom_report.json

Requiere:
    - Redis server corriendo
    - Credenciales en .env (REDIS_HOST, REDIS_PORT, REDIS_PASSWORD)
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse

# Agregar directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import redis.asyncio as aioredis
except ImportError:
    print("❌ Error: redis-py no instalado. Ejecutar: pip install redis")
    sys.exit(1)


class RedisAnalyzer:
    """
    Analizador de cache Redis con métricas detalladas.

    Conecta a Redis y recopila estadísticas sobre:
    - Cantidad de keys por patrón
    - TTL promedio por tipo de key
    - Keys sin expiración (PERSIST)
    - Memory usage por tipo
    - Recomendaciones de optimización
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
    ):
        """
        Inicializa el analizador.

        Args:
            host: Redis host (default: localhost)
            port: Redis port (default: 6379)
            password: Redis password (opcional)
            db: Database number (default: 0)
        """
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.client: Optional[aioredis.Redis] = None

        # Patrones de keys a analizar
        self.patterns = [
            "availability:*",
            "session:*",
            "lock:*",
            "rate_limit:*",
            "circuit_breaker:*",
            "tenant:*",
            "pms_cache:*",
        ]

    async def connect(self):
        """Conecta a Redis."""
        try:
            self.client = await aioredis.from_url(
                f"redis://{self.host}:{self.port}/{self.db}",
                password=self.password,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )

            # Test connection
            await self.client.ping()
            print(f"✅ Conectado a Redis: {self.host}:{self.port}")

        except Exception as e:
            print(f"❌ Error conectando a Redis: {e}")
            raise

    async def close(self):
        """Cierra la conexión a Redis."""
        if self.client:
            await self.client.close()
            print("🔌 Conexión cerrada")

    async def analyze_pattern(self, pattern: str) -> Dict[str, Any]:
        """
        Analiza keys que cumplen un patrón específico.

        Args:
            pattern: Patrón de keys (ej: "session:*")

        Returns:
            Dict con métricas del patrón:
            - count: Número de keys
            - ttl_avg: TTL promedio en segundos
            - no_ttl: Número de keys sin TTL
            - sample_keys: Muestra de 5 keys
            - memory_usage: Uso de memoria estimado
        """
        if not self.client:
            raise RuntimeError("Cliente Redis no conectado")

        keys = []
        cursor = 0

        # Usar SCAN para iterar todas las keys sin bloquear
        while True:
            cursor, batch = await self.client.scan(cursor=cursor, match=pattern, count=100)
            keys.extend(batch)
            if cursor == 0:
                break

        if not keys:
            return {
                "pattern": pattern,
                "count": 0,
                "ttl_avg": None,
                "ttl_min": None,
                "ttl_max": None,
                "no_ttl": 0,
                "sample_keys": [],
                "memory_usage_bytes": 0,
            }

        # Analizar TTL de todas las keys
        ttls = []
        no_ttl_count = 0
        memory_usage = 0

        for key in keys[:1000]:  # Limitar a 1000 keys para performance
            try:
                ttl = await self.client.ttl(key)

                if ttl == -1:  # Key sin TTL
                    no_ttl_count += 1
                elif ttl > 0:  # TTL válido
                    ttls.append(ttl)

                # Estimar memory usage
                memory_usage += await self.client.memory_usage(key) or 0

            except Exception as e:
                print(f"⚠️  Error analizando key {key}: {e}")
                continue

        ttl_avg = sum(ttls) / len(ttls) if ttls else 0
        ttl_min = min(ttls) if ttls else 0
        ttl_max = max(ttls) if ttls else 0

        return {
            "pattern": pattern,
            "count": len(keys),
            "ttl_avg": round(ttl_avg, 2),
            "ttl_min": ttl_min,
            "ttl_max": ttl_max,
            "no_ttl": no_ttl_count,
            "sample_keys": keys[:5],  # Muestra de 5 keys
            "memory_usage_bytes": memory_usage,
        }

    async def get_redis_info(self) -> Dict[str, Any]:
        """
        Obtiene información general de Redis.

        Returns:
            Dict con métricas de Redis server
        """
        if not self.client:
            raise RuntimeError("Cliente Redis no conectado")

        info = await self.client.info()

        return {
            "redis_version": info.get("redis_version"),
            "used_memory": info.get("used_memory"),
            "used_memory_human": info.get("used_memory_human"),
            "used_memory_peak": info.get("used_memory_peak"),
            "used_memory_peak_human": info.get("used_memory_peak_human"),
            "connected_clients": info.get("connected_clients"),
            "blocked_clients": info.get("blocked_clients"),
            "total_connections_received": info.get("total_connections_received"),
            "total_commands_processed": info.get("total_commands_processed"),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec"),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "evicted_keys": info.get("evicted_keys", 0),
            "expired_keys": info.get("expired_keys", 0),
        }

    def calculate_hit_ratio(self, info: Dict[str, Any]) -> float:
        """
        Calcula hit ratio del cache.

        Args:
            info: Dict con métricas de Redis (de get_redis_info)

        Returns:
            Hit ratio (0.0 - 1.0)
        """
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses

        if total == 0:
            return 0.0

        return hits / total

    def generate_recommendations(self, patterns_data: List[Dict[str, Any]], redis_info: Dict[str, Any]) -> List[str]:
        """
        Genera recomendaciones de optimización.

        Args:
            patterns_data: Lista de análisis por patrón
            redis_info: Info general de Redis

        Returns:
            Lista de recomendaciones en string
        """
        recommendations = []

        # Recomendación 1: Keys sin TTL
        for pattern_data in patterns_data:
            if pattern_data["no_ttl"] > 0:
                recommendations.append(
                    f"⚠️  {pattern_data['pattern']}: {pattern_data['no_ttl']} keys sin TTL. "
                    f"Considerar agregar expiración para prevenir crecimiento infinito."
                )

        # Recomendación 2: Hit ratio bajo
        hit_ratio = self.calculate_hit_ratio(redis_info)
        if hit_ratio < 0.7:
            recommendations.append(
                f"⚠️  Hit ratio bajo ({hit_ratio:.1%}). "
                f"Considerar: aumentar TTL de keys frecuentes, precalentar cache, "
                f"revisar lógica de invalidación."
            )

        # Recomendación 3: Evicted keys
        evicted = redis_info.get("evicted_keys", 0)
        if evicted > 1000:
            recommendations.append(
                f"⚠️  {evicted} keys evicted. Memoria insuficiente. "
                f"Considerar: aumentar maxmemory, reducir TTL de keys poco usadas."
            )

        # Recomendación 4: TTL muy cortos
        for pattern_data in patterns_data:
            if pattern_data["ttl_avg"] and pattern_data["ttl_avg"] < 60:
                recommendations.append(
                    f"💡 {pattern_data['pattern']}: TTL promedio muy corto ({pattern_data['ttl_avg']}s). "
                    f"Considerar aumentar a 300s+ para mejorar hit ratio."
                )

        # Recomendación 5: TTL muy largos
        for pattern_data in patterns_data:
            if pattern_data["ttl_avg"] and pattern_data["ttl_avg"] > 3600:
                recommendations.append(
                    f"💡 {pattern_data['pattern']}: TTL promedio muy largo ({pattern_data['ttl_avg']}s). "
                    f"Considerar reducir si los datos cambian frecuentemente."
                )

        if not recommendations:
            recommendations.append("✅ Cache en buen estado, no se detectaron problemas.")

        return recommendations

    async def analyze(self) -> Dict[str, Any]:
        """
        Ejecuta análisis completo de Redis cache.

        Returns:
            Dict con reporte completo de análisis
        """
        print("🔍 Analizando Redis cache...")

        # Conectar
        await self.connect()

        try:
            # Obtener info general
            redis_info = await self.get_redis_info()
            hit_ratio = self.calculate_hit_ratio(redis_info)

            print(f"📊 Hit ratio: {hit_ratio:.1%}")
            print(f"💾 Memoria usada: {redis_info['used_memory_human']}")

            # Analizar cada patrón
            patterns_data = []
            for pattern in self.patterns:
                print(f"🔎 Analizando patrón: {pattern}")
                pattern_analysis = await self.analyze_pattern(pattern)
                patterns_data.append(pattern_analysis)

                if pattern_analysis["count"] > 0:
                    print(f"  - {pattern_analysis['count']} keys")
                    print(f"  - TTL promedio: {pattern_analysis['ttl_avg']}s")
                    print(f"  - Keys sin TTL: {pattern_analysis['no_ttl']}")

            # Generar recomendaciones
            recommendations = self.generate_recommendations(patterns_data, redis_info)

            # Construir reporte
            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "redis_connection": {
                    "host": self.host,
                    "port": self.port,
                    "db": self.db,
                },
                "redis_info": redis_info,
                "cache_metrics": {
                    "hit_ratio": round(hit_ratio, 4),
                    "total_keys": sum(p["count"] for p in patterns_data),
                    "total_memory_bytes": sum(p["memory_usage_bytes"] for p in patterns_data),
                },
                "patterns": patterns_data,
                "recommendations": recommendations,
            }

            return report

        finally:
            await self.close()


async def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Análisis de Redis cache para Agente Hotelero IA")
    parser.add_argument("--host", default="localhost", help="Redis host (default: localhost)")
    parser.add_argument("--port", type=int, default=6379, help="Redis port (default: 6379)")
    parser.add_argument("--password", default=None, help="Redis password (opcional)")
    parser.add_argument("--db", type=int, default=0, help="Redis database number (default: 0)")
    parser.add_argument(
        "--output",
        default=".playbook/redis_analysis.json",
        help="Archivo de salida (default: .playbook/redis_analysis.json)",
    )

    args = parser.parse_args()

    # Crear directorio de salida si no existe
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ejecutar análisis
    analyzer = RedisAnalyzer(
        host=args.host,
        port=args.port,
        password=args.password,
        db=args.db,
    )

    try:
        report = await analyzer.analyze()

        # Guardar reporte
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n✅ Reporte generado: {output_path}")
        print("\n📋 Recomendaciones:")
        for recommendation in report["recommendations"]:
            print(f"  {recommendation}")

        return 0

    except Exception as e:
        print(f"\n❌ Error durante análisis: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
