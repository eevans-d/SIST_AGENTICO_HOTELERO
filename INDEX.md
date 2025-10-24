# 📑 ÍNDICE MAESTRO - AGENTE HOTELERO IA

**Estado Actual**: ✅ En Producción (Fly.io - São Paulo, Brasil)  
**URL**: https://agente-hotel-api.fly.dev  
**Última Actualización**: October 24, 2025

---

## 🎯 COMIENZA AQUÍ

### 🔴 URGENTE - SI NECESITAS ENTENDER QUÉ PASÓ

👉 **Lee primero**: [`DIA_6_DEPLOYMENT_FLY_IO_COMPLETADO.md`](DIA_6_DEPLOYMENT_FLY_IO_COMPLETADO.md)

Este documento contiene:
- Estado actual de la aplicación ✅
- Dónde está deployada (Fly.io, Brasil)
- Cómo monitorearla
- Próximos pasos
- Todo lo que necesitas saber para el futuro

---

## 📚 DOCUMENTACIÓN POR TEMA

### 🏨 Aplicación Principal
| Archivo | Descripción |
|---------|-------------|
| `agente-hotel-api/` | Código fuente de la API |
| `agente-hotel-api/app/main.py` | Punto de entrada FastAPI |

### ☁️ Deployment & Fly.io
| Archivo | Descripción | Estado |
|---------|-------------|--------|
| `DIA_6_DEPLOYMENT_FLY_IO_COMPLETADO.md` | **DOCUMENTO MAESTRO** | ✅ ACTIVO |
| `fly.toml` | Configuración de Fly.io | ✅ En uso |
| `Dockerfile` | Imagen Docker para producción | ✅ En uso |

### 🛠️ Scripts & Configuración
| Archivo | Descripción |
|---------|-------------|
| `deploy-fly.sh` | Script automatizado de deployment |
| `setup-fly-secrets.sh` | Script para configurar secrets |
| `requirements-prod.txt` | Dependencias de producción |
| `pyproject.toml` | Configuración Poetry |

---

## 🎮 COMANDOS RÁPIDOS

### Monitoreo
```bash
flyctl status
flyctl logs -f
flyctl logs -n
```

### Deployment
```bash
flyctl deploy
flyctl releases list
flyctl releases rollback
```

### Secrets
```bash
flyctl secrets list
flyctl secrets set KEY=VALUE
```

---

## 📊 INFORMACIÓN CRÍTICA

### 🌐 Ubicación
- **Región**: São Paulo, Brasil (gru)
- **URL**: https://agente-hotel-api.fly.dev
- **Health**: https://agente-hotel-api.fly.dev/health/live

### 👤 Acceso
- **Fly.io**: eevans.d@gmail.com ✅
- **GitHub**: eevans-d ✅
- **Repo**: SIST_AGENTICO_HOTELERO (main branch)

---

## 🚀 PRÓXIMAS ACCIONES

### 🔴 Inmediato
- [x] Deployment completado
- [x] Health checks pasando
- [ ] Revisar logs por 1 hora
- [ ] Curl a health/live

### 🟡 Corto Plazo (3-7 días)
- [ ] PostgreSQL externo
- [ ] Redis externo
- [ ] WhatsApp integrado

### 🟢 Mediano Plazo (2-4 semanas)
- [ ] Dominio personalizado
- [ ] Evaluar escalado
- [ ] Configurar backups

---

## ✅ CHECKLIST DIARIO

```bash
flyctl status
curl https://agente-hotel-api.fly.dev/health/live
flyctl logs -n | grep ERROR
```

---

**Documento Maestro**: [`DIA_6_DEPLOYMENT_FLY_IO_COMPLETADO.md`](DIA_6_DEPLOYMENT_FLY_IO_COMPLETADO.md)  
**Última revisión**: October 24, 2025
