"""
Database Performance Tuner para Agente Hotelero IA System
Optimización automática de queries, índices y configuración de base de datos
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
import json
from datetime import datetime, timedelta

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.engine import Row
from prometheus_client import Histogram, Counter, Gauge

from app.core.database import AsyncSessionFactory
from app.core.settings import settings

# Configurar logging
logger = logging.getLogger(__name__)

# Métricas de Prometheus
db_tuning_duration = Histogram(
    'db_tuning_duration_seconds',
    'Tiempo tomado por operaciones de tuning de DB',
    ['operation']
)

db_performance_metrics = Gauge(
    'db_performance_metrics',
    'Métricas de performance de base de datos',
    ['metric_type']
)

db_optimization_actions = Counter(
    'db_optimization_actions_total',
    'Total de acciones de optimización de DB ejecutadas',
    ['action_type', 'status']
)

class QueryOptimizationType(Enum):
    """Tipos de optimización de queries"""
    INDEX_CREATION = "index_creation"
    INDEX_REMOVAL = "index_removal"
    QUERY_REWRITE = "query_rewrite"
    STATISTICS_UPDATE = "statistics_update"
    VACUUM_ANALYZE = "vacuum_analyze"
    CONFIGURATION_TUNE = "configuration_tune"

@dataclass
class SlowQuery:
    """Información de query lenta"""
    query: str
    mean_time: float
    calls: int
    total_time: float
    rows: int
    query_id: str
    first_seen: datetime
    last_seen: datetime

@dataclass
class IndexRecommendation:
    """Recomendación de índice"""
    table_name: str
    columns: List[str]
    index_type: str  # btree, gin, gist, etc.
    estimated_benefit: float
    reason: str
    query_pattern: str

@dataclass
class DatabaseStats:
    """Estadísticas de base de datos"""
    total_size: int
    table_count: int
    index_count: int
    active_connections: int
    idle_connections: int
    slow_queries_count: int
    cache_hit_ratio: float
    checkpoint_frequency: float
    wal_size: int

class DatabasePerformanceTuner:
    """
    Tuner automático de performance de base de datos
    Analiza queries, recomienda índices y optimiza configuración
    """
    
    def __init__(self):
        self.db_engine = None
        self.slow_query_threshold = 1000  # 1 segundo en ms
        self.index_recommendations: List[IndexRecommendation] = []
        self.optimization_history: List[Dict] = []
        
    async def start(self):
        """Inicializar el tuner de DB"""
        try:
            self.db_engine = create_async_engine(
                settings.postgres_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )
            
            # Habilitar pg_stat_statements si no está habilitado
            await self._ensure_pg_stat_statements()
            
            logger.info("Database Performance Tuner iniciado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar DB Performance Tuner: {e}")
            raise
    
    async def stop(self):
        """Detener el tuner"""
        if self.db_engine:
            await self.db_engine.dispose()
        logger.info("Database Performance Tuner detenido")
    
    async def _ensure_pg_stat_statements(self):
        """Asegurar que pg_stat_statements esté habilitado"""
        try:
            async with AsyncSessionFactory() as session:
                # Verificar si pg_stat_statements está disponible
                result = await session.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                    )
                """))
                
                if not result.scalar():
                    # Intentar crear la extensión
                    try:
                        await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))
                        await session.commit()
                        logger.info("Extensión pg_stat_statements habilitada")
                    except Exception as e:
                        logger.warning(f"No se pudo habilitar pg_stat_statements: {e}")
                
        except Exception as e:
            logger.warning(f"Error verificando pg_stat_statements: {e}")
    
    async def analyze_slow_queries(self) -> List[SlowQuery]:
        """Analizar queries lentas"""
        with db_tuning_duration.labels('slow_query_analysis').time():
            try:
                async with AsyncSessionFactory() as session:
                    result = await session.execute(text("""
                        SELECT 
                            query,
                            mean_time,
                            calls,
                            total_time,
                            rows,
                            queryid::text as query_id
                        FROM pg_stat_statements 
                        WHERE mean_time > :threshold
                        ORDER BY mean_time DESC 
                        LIMIT 20
                    """), {'threshold': self.slow_query_threshold})
                    
                    slow_queries = []
                    for row in result:
                        slow_query = SlowQuery(
                            query=row.query,
                            mean_time=row.mean_time,
                            calls=row.calls,
                            total_time=row.total_time,
                            rows=row.rows,
                            query_id=row.query_id,
                            first_seen=datetime.now() - timedelta(hours=1),  # Estimado
                            last_seen=datetime.now()
                        )
                        slow_queries.append(slow_query)
                    
                    # Actualizar métrica
                    db_performance_metrics.labels('slow_queries_count').set(len(slow_queries))
                    
                    logger.info(f"Encontradas {len(slow_queries)} queries lentas")
                    return slow_queries
                    
            except Exception as e:
                logger.error(f"Error analizando queries lentas: {e}")
                return []
    
    async def generate_index_recommendations(self, slow_queries: List[SlowQuery]) -> List[IndexRecommendation]:
        """Generar recomendaciones de índices basadas en queries lentas"""
        with db_tuning_duration.labels('index_recommendations').time():
            recommendations = []
            
            try:
                for query in slow_queries:
                    query_recommendations = await self._analyze_query_for_indexes(query)
                    recommendations.extend(query_recommendations)
                
                # Eliminar duplicados y ordenar por beneficio estimado
                unique_recommendations = self._deduplicate_recommendations(recommendations)
                unique_recommendations.sort(key=lambda x: x.estimated_benefit, reverse=True)
                
                self.index_recommendations = unique_recommendations[:10]  # Top 10
                
                logger.info(f"Generadas {len(self.index_recommendations)} recomendaciones de índices")
                return self.index_recommendations
                
            except Exception as e:
                logger.error(f"Error generando recomendaciones de índices: {e}")
                return []
    
    async def _analyze_query_for_indexes(self, slow_query: SlowQuery) -> List[IndexRecommendation]:
        """Analizar una query específica para recomendaciones de índices"""
        recommendations = []
        
        try:
            # Análisis básico de patrones en la query
            query_lower = slow_query.query.lower()
            
            # Buscar patrones WHERE
            if 'where' in query_lower:
                # Extraer columnas en WHERE clauses
                where_columns = self._extract_where_columns(slow_query.query)
                for table, columns in where_columns.items():
                    if columns:
                        recommendation = IndexRecommendation(
                            table_name=table,
                            columns=columns,
                            index_type='btree',
                            estimated_benefit=min(slow_query.mean_time / 1000 * 0.7, 0.9),
                            reason=f"WHERE clause en columnas {', '.join(columns)}",
                            query_pattern=slow_query.query[:100] + "..."
                        )
                        recommendations.append(recommendation)
            
            # Buscar patrones JOIN
            if 'join' in query_lower:
                join_columns = self._extract_join_columns(slow_query.query)
                for table, columns in join_columns.items():
                    if columns:
                        recommendation = IndexRecommendation(
                            table_name=table,
                            columns=columns,
                            index_type='btree',
                            estimated_benefit=min(slow_query.mean_time / 1000 * 0.6, 0.8),
                            reason=f"JOIN en columnas {', '.join(columns)}",
                            query_pattern=slow_query.query[:100] + "..."
                        )
                        recommendations.append(recommendation)
            
            # Buscar patrones ORDER BY
            if 'order by' in query_lower:
                order_columns = self._extract_order_columns(slow_query.query)
                for table, columns in order_columns.items():
                    if columns:
                        recommendation = IndexRecommendation(
                            table_name=table,
                            columns=columns,
                            index_type='btree',
                            estimated_benefit=min(slow_query.mean_time / 1000 * 0.5, 0.7),
                            reason=f"ORDER BY en columnas {', '.join(columns)}",
                            query_pattern=slow_query.query[:100] + "..."
                        )
                        recommendations.append(recommendation)
            
        except Exception as e:
            logger.warning(f"Error analizando query para índices: {e}")
        
        return recommendations
    
    def _extract_where_columns(self, query: str) -> Dict[str, List[str]]:
        """Extraer columnas de WHERE clauses (implementación simplificada)"""
        # Esta es una implementación básica
        # En producción usaríamos un parser SQL más sofisticado
        result = {}
        
        try:
            query_lower = query.lower()
            if 'reservations' in query_lower and 'guest_name' in query_lower:
                result['reservations'] = ['guest_name']
            if 'reservations' in query_lower and 'check_in_date' in query_lower:
                result.setdefault('reservations', []).append('check_in_date')
            if 'rooms' in query_lower and 'room_type' in query_lower:
                result['rooms'] = ['room_type']
            if 'sessions' in query_lower and 'user_id' in query_lower:
                result['sessions'] = ['user_id']
        except Exception:
            pass
        
        return result
    
    def _extract_join_columns(self, query: str) -> Dict[str, List[str]]:
        """Extraer columnas de JOIN clauses"""
        result = {}
        
        try:
            query_lower = query.lower()
            if 'join' in query_lower:
                # Patrones comunes de JOIN en el sistema hotelero
                if 'reservations.room_id = rooms.id' in query_lower:
                    result['reservations'] = ['room_id']
                    result['rooms'] = ['id']
                if 'sessions.user_id = users.id' in query_lower:
                    result['sessions'] = ['user_id']
                    result['users'] = ['id']
        except Exception:
            pass
        
        return result
    
    def _extract_order_columns(self, query: str) -> Dict[str, List[str]]:
        """Extraer columnas de ORDER BY clauses"""
        result = {}
        
        try:
            query_lower = query.lower()
            if 'order by' in query_lower:
                if 'created_at' in query_lower:
                    # Determinar tabla por contexto
                    if 'reservations' in query_lower:
                        result['reservations'] = ['created_at']
                    elif 'sessions' in query_lower:
                        result['sessions'] = ['created_at']
                if 'updated_at' in query_lower:
                    if 'reservations' in query_lower:
                        result['reservations'] = ['updated_at']
        except Exception:
            pass
        
        return result
    
    def _deduplicate_recommendations(self, recommendations: List[IndexRecommendation]) -> List[IndexRecommendation]:
        """Eliminar recomendaciones duplicadas"""
        seen = set()
        unique = []
        
        for rec in recommendations:
            key = (rec.table_name, tuple(sorted(rec.columns)), rec.index_type)
            if key not in seen:
                seen.add(key)
                unique.append(rec)
        
        return unique
    
    async def create_recommended_indexes(self, limit: int = 3) -> List[Dict]:
        """Crear índices recomendados (limitado para seguridad)"""
        created_indexes = []
        
        try:
            # Solo crear los índices con mayor beneficio estimado
            top_recommendations = self.index_recommendations[:limit]
            
            for rec in top_recommendations:
                success = await self._create_index(rec)
                
                result = {
                    'table': rec.table_name,
                    'columns': rec.columns,
                    'type': rec.index_type,
                    'success': success,
                    'reason': rec.reason
                }
                created_indexes.append(result)
                
                # Registrar acción
                status = 'success' if success else 'failed'
                db_optimization_actions.labels('index_creation', status).inc()
                
                # Pausa entre creaciones para no sobrecargar
                await asyncio.sleep(2)
            
            logger.info(f"Proceso de creación de índices completado: {len(created_indexes)} índices procesados")
            
        except Exception as e:
            logger.error(f"Error en creación de índices: {e}")
        
        return created_indexes
    
    async def _create_index(self, recommendation: IndexRecommendation) -> bool:
        """Crear un índice específico"""
        try:
            async with AsyncSessionFactory() as session:
                # Generar nombre de índice
                columns_str = '_'.join(recommendation.columns)
                index_name = f"idx_{recommendation.table_name}_{columns_str}"
                
                # Verificar si el índice ya existe
                result = await session.execute(text("""
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = :table AND indexname = :index
                """), {'table': recommendation.table_name, 'index': index_name})
                
                if result.fetchone():
                    logger.info(f"Índice {index_name} ya existe")
                    return True
                
                # Crear índice de forma concurrente (no bloquea)
                columns_list = ', '.join(recommendation.columns)
                create_sql = f"""
                    CREATE INDEX CONCURRENTLY {index_name} 
                    ON {recommendation.table_name} USING {recommendation.index_type} ({columns_list})
                """
                
                await session.execute(text(create_sql))
                await session.commit()
                
                logger.info(f"Índice creado exitosamente: {index_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error creando índice para {recommendation.table_name}: {e}")
            return False
    
    async def analyze_unused_indexes(self) -> List[Dict]:
        """Analizar índices no utilizados"""
        with db_tuning_duration.labels('unused_index_analysis').time():
            try:
                async with AsyncSessionFactory() as session:
                    result = await session.execute(text("""
                        SELECT 
                            schemaname,
                            tablename,
                            indexname,
                            idx_scan,
                            idx_tup_read,
                            idx_tup_fetch,
                            pg_size_pretty(pg_relation_size(indexrelid)) as size
                        FROM pg_stat_user_indexes 
                        WHERE idx_scan < 10  -- Usado menos de 10 veces
                        AND schemaname = 'public'
                        ORDER BY pg_relation_size(indexrelid) DESC
                    """))
                    
                    unused_indexes = []
                    for row in result:
                        unused_indexes.append({
                            'schema': row.schemaname,
                            'table': row.tablename,
                            'index': row.indexname,
                            'scans': row.idx_scan,
                            'size': row.size,
                            'recommendation': 'Consider dropping if confirmed unused'
                        })
                    
                    logger.info(f"Encontrados {len(unused_indexes)} índices potencialmente no utilizados")
                    return unused_indexes
                    
            except Exception as e:
                logger.error(f"Error analizando índices no utilizados: {e}")
                return []
    
    async def optimize_database_configuration(self) -> Dict:
        """Optimizar configuración de la base de datos"""
        with db_tuning_duration.labels('config_optimization').time():
            optimizations = {}
            
            try:
                async with AsyncSessionFactory() as session:
                    # Obtener estadísticas actuales
                    stats = await self._get_database_stats(session)
                    
                    # Optimizar configuración basada en estadísticas
                    config_changes = []
                    
                    # Shared buffers (25% de RAM disponible)
                    shared_buffers = await self._calculate_optimal_shared_buffers()
                    if shared_buffers:
                        config_changes.append(('shared_buffers', shared_buffers))
                    
                    # Work memory
                    work_mem = await self._calculate_optimal_work_mem()
                    if work_mem:
                        config_changes.append(('work_mem', work_mem))
                    
                    # Maintenance work memory
                    maintenance_work_mem = await self._calculate_optimal_maintenance_work_mem()
                    if maintenance_work_mem:
                        config_changes.append(('maintenance_work_mem', maintenance_work_mem))
                    
                    # Checkpoint settings
                    checkpoint_completion_target = 0.9
                    config_changes.append(('checkpoint_completion_target', checkpoint_completion_target))
                    
                    # WAL settings
                    wal_buffers = '16MB'
                    config_changes.append(('wal_buffers', wal_buffers))
                    
                    optimizations = {
                        'current_stats': stats,
                        'recommended_changes': config_changes,
                        'note': 'Changes require PostgreSQL restart to take effect'
                    }
                    
                    logger.info(f"Generadas {len(config_changes)} recomendaciones de configuración")
                    
            except Exception as e:
                logger.error(f"Error optimizando configuración: {e}")
                optimizations = {'error': str(e)}
            
            return optimizations
    
    async def _get_database_stats(self, session: AsyncSession) -> DatabaseStats:
        """Obtener estadísticas actuales de la base de datos"""
        try:
            # Tamaño total de la base de datos
            result = await session.execute(text("SELECT pg_database_size(current_database())"))
            total_size = result.scalar()
            
            # Número de tablas
            result = await session.execute(text("""
                SELECT count(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = result.scalar()
            
            # Número de índices
            result = await session.execute(text("""
                SELECT count(*) FROM pg_indexes WHERE schemaname = 'public'
            """))
            index_count = result.scalar()
            
            # Conexiones activas e idle
            result = await session.execute(text("""
                SELECT 
                    count(*) FILTER (WHERE state = 'active') as active,
                    count(*) FILTER (WHERE state = 'idle') as idle
                FROM pg_stat_activity
            """))
            row = result.fetchone()
            active_connections = row.active or 0
            idle_connections = row.idle or 0
            
            # Cache hit ratio
            result = await session.execute(text("""
                SELECT 
                    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
                FROM pg_statio_user_tables
            """))
            cache_hit_ratio = result.scalar() or 0.0
            
            return DatabaseStats(
                total_size=total_size or 0,
                table_count=table_count or 0,
                index_count=index_count or 0,
                active_connections=active_connections,
                idle_connections=idle_connections,
                slow_queries_count=0,  # Se actualiza en otro método
                cache_hit_ratio=float(cache_hit_ratio),
                checkpoint_frequency=0.0,  # Requiere análisis temporal
                wal_size=0  # Requiere consulta específica
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de DB: {e}")
            return DatabaseStats(0, 0, 0, 0, 0, 0, 0.0, 0.0, 0)
    
    async def _calculate_optimal_shared_buffers(self) -> Optional[str]:
        """Calcular shared_buffers óptimo"""
        try:
            # 25% de la RAM disponible (simplificado)
            import psutil
            total_memory = psutil.virtual_memory().total
            optimal_shared_buffers = int(total_memory * 0.25 / (1024 * 1024))  # MB
            
            # Límites razonables
            if optimal_shared_buffers < 128:
                optimal_shared_buffers = 128
            elif optimal_shared_buffers > 8192:
                optimal_shared_buffers = 8192
            
            return f"{optimal_shared_buffers}MB"
        except Exception:
            return None
    
    async def _calculate_optimal_work_mem(self) -> Optional[str]:
        """Calcular work_mem óptimo"""
        try:
            # Basado en conexiones esperadas y memoria disponible
            import psutil
            total_memory = psutil.virtual_memory().total
            max_connections = 100  # Asumido
            work_mem = int((total_memory * 0.05) / max_connections / (1024 * 1024))  # MB
            
            # Límites razonables
            if work_mem < 4:
                work_mem = 4
            elif work_mem > 256:
                work_mem = 256
            
            return f"{work_mem}MB"
        except Exception:
            return None
    
    async def _calculate_optimal_maintenance_work_mem(self) -> Optional[str]:
        """Calcular maintenance_work_mem óptimo"""
        try:
            # 5% de la RAM disponible
            import psutil
            total_memory = psutil.virtual_memory().total
            maintenance_work_mem = int(total_memory * 0.05 / (1024 * 1024))  # MB
            
            # Límites razonables
            if maintenance_work_mem < 64:
                maintenance_work_mem = 64
            elif maintenance_work_mem > 2048:
                maintenance_work_mem = 2048
            
            return f"{maintenance_work_mem}MB"
        except Exception:
            return None
    
    async def vacuum_analyze_all(self) -> Dict:
        """Ejecutar VACUUM ANALYZE en todas las tablas principales"""
        with db_tuning_duration.labels('vacuum_analyze').time():
            try:
                async with AsyncSessionFactory() as session:
                    # Obtener lista de tablas principales
                    result = await session.execute(text("""
                        SELECT tablename FROM pg_tables 
                        WHERE schemaname = 'public' 
                        AND tablename IN ('reservations', 'rooms', 'sessions', 'users', 'messages')
                    """))
                    
                    tables = [row.tablename for row in result]
                    processed_tables = []
                    
                    for table in tables:
                        try:
                            # VACUUM ANALYZE específico por tabla
                            await session.execute(text(f"VACUUM ANALYZE {table}"))
                            processed_tables.append({'table': table, 'status': 'success'})
                            logger.info(f"VACUUM ANALYZE completado para tabla: {table}")
                        except Exception as e:
                            processed_tables.append({'table': table, 'status': 'failed', 'error': str(e)})
                            logger.warning(f"Error en VACUUM ANALYZE para {table}: {e}")
                    
                    await session.commit()
                    
                    # Registrar acción
                    db_optimization_actions.labels('vacuum_analyze', 'success').inc()
                    
                    return {
                        'status': 'completed',
                        'tables_processed': len(processed_tables),
                        'results': processed_tables
                    }
                    
            except Exception as e:
                logger.error(f"Error en VACUUM ANALYZE: {e}")
                db_optimization_actions.labels('vacuum_analyze', 'failed').inc()
                return {'status': 'failed', 'error': str(e)}
    
    async def get_performance_report(self) -> Dict:
        """Obtener reporte completo de performance de DB"""
        try:
            # Recopilar datos para el reporte
            slow_queries = await self.analyze_slow_queries()
            unused_indexes = await self.analyze_unused_indexes()
            
            async with AsyncSessionFactory() as session:
                db_stats = await self._get_database_stats(session)
            
            return {
                'database_stats': {
                    'total_size_mb': db_stats.total_size // (1024 * 1024),
                    'table_count': db_stats.table_count,
                    'index_count': db_stats.index_count,
                    'active_connections': db_stats.active_connections,
                    'idle_connections': db_stats.idle_connections,
                    'cache_hit_ratio': round(db_stats.cache_hit_ratio, 4)
                },
                'slow_queries': {
                    'count': len(slow_queries),
                    'queries': [
                        {
                            'query_snippet': q.query[:100] + "..." if len(q.query) > 100 else q.query,
                            'mean_time_ms': round(q.mean_time, 2),
                            'calls': q.calls,
                            'total_time_ms': round(q.total_time, 2)
                        }
                        for q in slow_queries[:5]
                    ]
                },
                'index_recommendations': {
                    'count': len(self.index_recommendations),
                    'top_recommendations': [
                        {
                            'table': rec.table_name,
                            'columns': rec.columns,
                            'estimated_benefit': round(rec.estimated_benefit, 2),
                            'reason': rec.reason
                        }
                        for rec in self.index_recommendations[:5]
                    ]
                },
                'unused_indexes': {
                    'count': len(unused_indexes),
                    'indexes': unused_indexes[:5]
                },
                'optimization_history': self.optimization_history[-10:],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte de performance: {e}")
            return {'error': str(e)}

# Instancia global del tuner
db_performance_tuner = DatabasePerformanceTuner()

async def get_db_performance_tuner() -> DatabasePerformanceTuner:
    """Obtener instancia del tuner de performance de DB"""
    return db_performance_tuner