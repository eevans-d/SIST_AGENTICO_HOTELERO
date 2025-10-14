#!/usr/bin/env python3
"""
Script de monitoreo de Connection Pool PostgreSQL para Agente Hotelero IA.

Monitorea el pool de conexiones de PostgreSQL para detectar:
- Conexiones activas vs disponibles en el pool
- Conexiones idle y long-running
- Pool cerca del límite (overflow)
- Queries lentas bloqueando conexiones
- Métricas exportables a Prometheus

Uso:
    python scripts/monitor_connections.py
    python scripts/monitor_connections.py --watch
    python scripts/monitor_connections.py --threshold 80 --alert

Requiere:
    - PostgreSQL corriendo
    - Credenciales en .env (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST)
    - asyncpg: pip install asyncpg
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import argparse
from dataclasses import dataclass, asdict

# Agregar directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import asyncpg
except ImportError:
    print("❌ Error: asyncpg no instalado. Ejecutar: pip install asyncpg")
    sys.exit(1)


@dataclass
class ConnectionStats:
    """Estadísticas de una conexión PostgreSQL."""
    pid: int
    user: str
    database: str
    state: str
    query: str
    duration_seconds: Optional[float]
    wait_event: Optional[str]
    backend_start: datetime
    state_change: Optional[datetime]


@dataclass
class PoolMetrics:
    """Métricas del pool de conexiones."""
    timestamp: str
    total_connections: int
    active_connections: int
    idle_connections: int
    idle_in_transaction: int
    waiting_connections: int
    long_running_queries: int
    pool_size_configured: int
    max_overflow_configured: int
    pool_utilization_percent: float
    overflow_in_use: int
    recommendations: List[str]


class PostgresConnectionMonitor:
    """
    Monitor de conexiones PostgreSQL con análisis de pool.
    
    Conecta a PostgreSQL y analiza:
    - pg_stat_activity para conexiones activas
    - Settings de pool_size y max_overflow
    - Identifica conexiones problemáticas
    - Genera alertas si pool cerca del límite
    - Exporta métricas para Prometheus
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "postgres",
        password: str = "postgres",
        database: str = "agente_hotel",
        pool_size: int = 10,
        max_overflow: int = 20,
        long_query_threshold_seconds: int = 30,
    ):
        """
        Inicializa el monitor.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            user: Database user
            password: Database password
            database: Database name
            pool_size: Configured pool size (from settings)
            max_overflow: Configured max overflow (from settings)
            long_query_threshold_seconds: Threshold para considerar query lenta
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.long_query_threshold = timedelta(seconds=long_query_threshold_seconds)
        self.conn: Optional[asyncpg.Connection] = None
    
    async def connect(self):
        """Conecta a PostgreSQL."""
        try:
            self.conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                timeout=10,
            )
            print(f"✅ Conectado a PostgreSQL: {self.host}:{self.port}/{self.database}")
            
        except Exception as e:
            print(f"❌ Error conectando a PostgreSQL: {e}")
            raise
    
    async def close(self):
        """Cierra la conexión."""
        if self.conn:
            await self.conn.close()
            print("🔌 Conexión cerrada")
    
    async def get_active_connections(self) -> List[ConnectionStats]:
        """
        Obtiene conexiones activas de pg_stat_activity.
        
        Returns:
            Lista de ConnectionStats con info de cada conexión
        """
        if not self.conn:
            raise RuntimeError("No hay conexión a PostgreSQL")
        
        query = """
            SELECT
                pid,
                usename as user,
                datname as database,
                state,
                COALESCE(query, '<no query>') as query,
                EXTRACT(EPOCH FROM (NOW() - query_start)) as duration_seconds,
                wait_event,
                backend_start,
                state_change
            FROM pg_stat_activity
            WHERE datname = $1
              AND pid != pg_backend_pid()  -- Excluir esta query
            ORDER BY query_start DESC NULLS LAST
        """
        
        rows = await self.conn.fetch(query, self.database)
        
        connections = []
        for row in rows:
            connections.append(ConnectionStats(
                pid=row['pid'],
                user=row['user'],
                database=row['database'],
                state=row['state'],
                query=row['query'][:200] if row['query'] else '<no query>',  # Truncar query larga
                duration_seconds=row['duration_seconds'],
                wait_event=row['wait_event'],
                backend_start=row['backend_start'],
                state_change=row['state_change'],
            ))
        
        return connections
    
    async def analyze_connections(self) -> PoolMetrics:
        """
        Analiza conexiones y genera métricas del pool.
        
        Returns:
            PoolMetrics con estadísticas completas
        """
        connections = await self.get_active_connections()
        
        # Contar por estado
        total = len(connections)
        active = sum(1 for c in connections if c.state == 'active')
        idle = sum(1 for c in connections if c.state == 'idle')
        idle_in_transaction = sum(1 for c in connections if c.state == 'idle in transaction')
        waiting = sum(1 for c in connections if c.wait_event)
        
        # Identificar queries lentas
        long_running = []
        for conn in connections:
            if conn.duration_seconds and conn.duration_seconds > self.long_query_threshold.total_seconds():
                long_running.append(conn)
        
        # Calcular utilización del pool
        total_pool_capacity = self.pool_size + self.max_overflow
        utilization = (total / total_pool_capacity * 100) if total_pool_capacity > 0 else 0
        overflow_in_use = max(0, total - self.pool_size)
        
        # Generar recomendaciones
        recommendations = self._generate_recommendations(
            total, active, idle, idle_in_transaction, long_running,
            utilization, overflow_in_use
        )
        
        return PoolMetrics(
            timestamp=datetime.utcnow().isoformat(),
            total_connections=total,
            active_connections=active,
            idle_connections=idle,
            idle_in_transaction=idle_in_transaction,
            waiting_connections=waiting,
            long_running_queries=len(long_running),
            pool_size_configured=self.pool_size,
            max_overflow_configured=self.max_overflow,
            pool_utilization_percent=round(utilization, 2),
            overflow_in_use=overflow_in_use,
            recommendations=recommendations,
        )
    
    def _generate_recommendations(
        self,
        total: int,
        active: int,
        idle: int,
        idle_in_transaction: int,
        long_running: List[ConnectionStats],
        utilization: float,
        overflow_in_use: int,
    ) -> List[str]:
        """
        Genera recomendaciones de optimización.
        
        Returns:
            Lista de recomendaciones
        """
        recommendations = []
        
        # Recomendación 1: Pool cerca del límite
        if utilization > 90:
            recommendations.append(
                f"🚨 CRÍTICO: Pool al {utilization:.1f}% de capacidad. "
                f"Aumentar pool_size (actual: {self.pool_size}) o max_overflow (actual: {self.max_overflow})."
            )
        elif utilization > 75:
            recommendations.append(
                f"⚠️  ADVERTENCIA: Pool al {utilization:.1f}% de capacidad. "
                f"Monitorear de cerca. Considerar aumentar pool_size."
            )
        
        # Recomendación 2: Overflow en uso
        if overflow_in_use > 0:
            recommendations.append(
                f"⚠️  {overflow_in_use} conexiones en overflow. "
                f"El pool base ({self.pool_size}) es insuficiente para la carga actual."
            )
        
        # Recomendación 3: Queries lentas
        if long_running:
            recommendations.append(
                f"⚠️  {len(long_running)} queries lentas (>{self.long_query_threshold.total_seconds()}s). "
                f"Revisar queries: {[f'PID {c.pid} ({c.duration_seconds:.1f}s)' for c in long_running[:3]]}"
            )
        
        # Recomendación 4: Idle in transaction
        if idle_in_transaction > 3:
            recommendations.append(
                f"⚠️  {idle_in_transaction} conexiones idle in transaction. "
                f"Posible transaction leak. Revisar commit/rollback en código."
            )
        
        # Recomendación 5: Demasiadas conexiones idle
        if idle > self.pool_size:
            recommendations.append(
                f"💡 {idle} conexiones idle (>{self.pool_size} pool_size). "
                f"Considerar reducir pool_size o implementar connection pooling externo (PgBouncer)."
            )
        
        # Recomendación 6: Pool subutilizado
        if utilization < 20 and total > 5:
            recommendations.append(
                f"💡 Pool subutilizado ({utilization:.1f}%). "
                f"Considerar reducir pool_size para liberar recursos."
            )
        
        if not recommendations:
            recommendations.append("✅ Pool en buen estado. Sin problemas detectados.")
        
        return recommendations
    
    async def get_slow_queries(self, limit: int = 10) -> List[ConnectionStats]:
        """
        Obtiene las queries más lentas actualmente ejecutándose.
        
        Args:
            limit: Número máximo de queries a retornar
        
        Returns:
            Lista de ConnectionStats ordenada por duración DESC
        """
        connections = await self.get_active_connections()
        
        # Filtrar solo queries con duración > threshold y estado active
        slow_queries = [
            c for c in connections
            if c.state == 'active'
            and c.duration_seconds
            and c.duration_seconds > self.long_query_threshold.total_seconds()
        ]
        
        # Ordenar por duración descendente
        slow_queries.sort(key=lambda x: x.duration_seconds or 0, reverse=True)
        
        return slow_queries[:limit]
    
    async def generate_prometheus_metrics(self) -> str:
        """
        Genera métricas en formato Prometheus.
        
        Returns:
            String con métricas en formato Prometheus text
        """
        metrics = await self.analyze_connections()
        
        prometheus_output = f"""# HELP db_pool_active_connections Number of active database connections
# TYPE db_pool_active_connections gauge
db_pool_active_connections {metrics.active_connections}

# HELP db_pool_idle_connections Number of idle database connections
# TYPE db_pool_idle_connections gauge
db_pool_idle_connections {metrics.idle_connections}

# HELP db_pool_total_connections Total database connections
# TYPE db_pool_total_connections gauge
db_pool_total_connections {metrics.total_connections}

# HELP db_pool_utilization_percent Pool utilization percentage
# TYPE db_pool_utilization_percent gauge
db_pool_utilization_percent {metrics.pool_utilization_percent}

# HELP db_pool_overflow Number of overflow connections in use
# TYPE db_pool_overflow gauge
db_pool_overflow {metrics.overflow_in_use}

# HELP db_pool_long_running_queries Number of long-running queries
# TYPE db_pool_long_running_queries gauge
db_pool_long_running_queries {metrics.long_running_queries}

# HELP db_pool_idle_in_transaction Number of idle in transaction connections
# TYPE db_pool_idle_in_transaction gauge
db_pool_idle_in_transaction {metrics.idle_in_transaction}

# HELP db_pool_size_configured Configured pool size
# TYPE db_pool_size_configured gauge
db_pool_size_configured {metrics.pool_size_configured}

# HELP db_pool_max_overflow_configured Configured max overflow
# TYPE db_pool_max_overflow_configured gauge
db_pool_max_overflow_configured {metrics.max_overflow_configured}
"""
        return prometheus_output
    
    async def monitor_loop(self, interval_seconds: int = 10, duration_seconds: int = 60):
        """
        Loop de monitoreo continuo.
        
        Args:
            interval_seconds: Intervalo entre mediciones
            duration_seconds: Duración total del monitoreo
        """
        print(f"🔄 Iniciando monitoreo continuo (intervalo: {interval_seconds}s, duración: {duration_seconds}s)")
        
        end_time = datetime.now() + timedelta(seconds=duration_seconds)
        
        while datetime.now() < end_time:
            metrics = await self.analyze_connections()
            
            print(f"\n⏰ {metrics.timestamp}")
            print(f"📊 Conexiones: {metrics.total_connections} total, "
                  f"{metrics.active_connections} active, "
                  f"{metrics.idle_connections} idle")
            print(f"📈 Utilización: {metrics.pool_utilization_percent}% "
                  f"({metrics.total_connections}/{metrics.pool_size_configured + metrics.max_overflow_configured})")
            
            if metrics.long_running_queries > 0:
                print(f"⚠️  {metrics.long_running_queries} queries lentas")
            
            if metrics.recommendations:
                print("\n💡 Recomendaciones:")
                for rec in metrics.recommendations:
                    print(f"  {rec}")
            
            await asyncio.sleep(interval_seconds)
        
        print("\n✅ Monitoreo completado")


async def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Monitoreo de Connection Pool PostgreSQL"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="PostgreSQL host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5432,
        help="PostgreSQL port (default: 5432)"
    )
    parser.add_argument(
        "--user",
        default="postgres",
        help="Database user (default: postgres)"
    )
    parser.add_argument(
        "--password",
        default="postgres",
        help="Database password"
    )
    parser.add_argument(
        "--database",
        default="agente_hotel",
        help="Database name (default: agente_hotel)"
    )
    parser.add_argument(
        "--pool-size",
        type=int,
        default=10,
        help="Configured pool size (default: 10)"
    )
    parser.add_argument(
        "--max-overflow",
        type=int,
        default=20,
        help="Configured max overflow (default: 20)"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=80,
        help="Alert threshold percentage (default: 80)"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuous monitoring mode"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Watch interval in seconds (default: 10)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Watch duration in seconds (default: 60)"
    )
    parser.add_argument(
        "--output",
        default=".playbook/connection_pool_report.json",
        help="Output file for JSON report"
    )
    parser.add_argument(
        "--prometheus",
        action="store_true",
        help="Output Prometheus metrics"
    )
    
    args = parser.parse_args()
    
    # Crear directorio de salida
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Crear monitor
    monitor = PostgresConnectionMonitor(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        pool_size=args.pool_size,
        max_overflow=args.max_overflow,
        long_query_threshold_seconds=30,
    )
    
    try:
        await monitor.connect()
        
        if args.watch:
            # Modo monitoreo continuo
            await monitor.monitor_loop(
                interval_seconds=args.interval,
                duration_seconds=args.duration
            )
        else:
            # Análisis único
            print("🔍 Analizando conexiones PostgreSQL...")
            
            metrics = await monitor.analyze_connections()
            connections = await monitor.get_active_connections()
            slow_queries = await monitor.get_slow_queries()
            
            # Mostrar resumen
            print(f"\n📊 Resumen de Conexiones")
            print(f"  Total: {metrics.total_connections}")
            print(f"  Active: {metrics.active_connections}")
            print(f"  Idle: {metrics.idle_connections}")
            print(f"  Idle in transaction: {metrics.idle_in_transaction}")
            print(f"  Waiting: {metrics.waiting_connections}")
            print(f"  Long-running queries: {metrics.long_running_queries}")
            
            print(f"\n📈 Pool Metrics")
            print(f"  Pool size: {metrics.pool_size_configured}")
            print(f"  Max overflow: {metrics.max_overflow_configured}")
            print(f"  Total capacity: {metrics.pool_size_configured + metrics.max_overflow_configured}")
            print(f"  Utilization: {metrics.pool_utilization_percent}%")
            print(f"  Overflow in use: {metrics.overflow_in_use}")
            
            if slow_queries:
                print(f"\n⚠️  Queries Lentas:")
                for query in slow_queries:
                    print(f"  PID {query.pid}: {query.duration_seconds:.2f}s - {query.query[:100]}...")
            
            print(f"\n💡 Recomendaciones:")
            for rec in metrics.recommendations:
                print(f"  {rec}")
            
            # Alerta si threshold excedido
            if metrics.pool_utilization_percent > args.threshold:
                print(f"\n🚨 ALERTA: Pool utilization ({metrics.pool_utilization_percent}%) "
                      f"excede threshold ({args.threshold}%)")
            
            # Guardar reporte JSON
            report = {
                "metrics": asdict(metrics),
                "connections": [asdict(c) for c in connections],
                "slow_queries": [asdict(c) for c in slow_queries],
            }
            
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"\n✅ Reporte guardado: {output_path}")
            
            # Output Prometheus si solicitado
            if args.prometheus:
                prom_metrics = await monitor.generate_prometheus_metrics()
                prom_file = output_path.parent / "connection_pool_metrics.prom"
                with open(prom_file, "w") as f:
                    f.write(prom_metrics)
                print(f"✅ Métricas Prometheus guardadas: {prom_file}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error durante monitoreo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        await monitor.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
