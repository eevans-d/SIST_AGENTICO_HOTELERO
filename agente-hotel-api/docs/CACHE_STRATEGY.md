## Estrategia de Cache (Esqueleto Fase 5)

| Operación | Capa | TTL Actual | TTL Propuesto | Invalidación | Notas |
|-----------|------|-----------|---------------|--------------|-------|
| PMS get_reservation | Redis KV | 300s | 180s | On update/cancel | Alta lectura |
| PMS availability_search | Redis KV | 60s | 45s | Tiempo natural | Volátil |
| Feature Flags | Redis Hash | 30s (local cache) | = | Set flag | Uso `feature_flags` |

Pendiente: añadir métricas de hit/miss y ratio objetivo ≥70%.
