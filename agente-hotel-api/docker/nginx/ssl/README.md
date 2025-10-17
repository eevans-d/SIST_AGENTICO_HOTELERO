# 🔐 SSL Certificates - Development Only

## ⚠️ IMPORTANTE: Certificados de Desarrollo

Los certificados en este directorio (`dev.crt` y `dev.key`) son **SOLO PARA DESARROLLO LOCAL** y deben ser reemplazados en producción.

### Para Desarrollo Local

Los certificados actuales son auto-firmados y seguros para desarrollo:

```bash
# Regenerar certificados de desarrollo (si es necesario)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout dev.key \
  -out dev.crt \
  -subj "/C=US/ST=State/L=City/O=Dev/CN=localhost"
```

### Para Producción

**🚨 NUNCA usar estos certificados en producción**

En producción debes:

1. **Usar certificados válidos** de una CA reconocida (Let's Encrypt, DigiCert, etc.)
2. **Almacenar secrets en vault** (AWS Secrets Manager, HashiCorp Vault, etc.)
3. **Configurar rotación automática** de certificados
4. **Usar permisos restrictivos** (600 para .key, 644 para .crt)

#### Opción 1: Let's Encrypt (Recomendado)

```bash
# Usar certbot para obtener certificados gratuitos
certbot certonly --standalone -d tu-dominio.com
```

#### Opción 2: Certificados Comerciales

Comprar certificados de CA reconocida y seguir sus instrucciones.

#### Opción 3: AWS Certificate Manager

Si usas AWS, ACM proporciona certificados gratuitos para ELB/CloudFront.

### Checklist de Seguridad Pre-Producción

- [ ] Certificados de producción instalados (NO los de dev)
- [ ] Private keys con permisos 600
- [ ] Certificados almacenados en secrets manager
- [ ] dev.key y dev.crt agregados a .gitignore de producción
- [ ] Configurado monitoreo de expiración de certificados
- [ ] Implementada rotación automática

### Verificar Certificados

```bash
# Ver detalles del certificado
openssl x509 -in dev.crt -text -noout

# Verificar key y cert coinciden
openssl x509 -noout -modulus -in dev.crt | openssl md5
openssl rsa -noout -modulus -in dev.key | openssl md5
```

---

**Última actualización**: 2025-01-XX  
**Ambiente**: Desarrollo local solamente  
**Estado**: ✅ Seguro para desarrollo, 🚨 NO USAR EN PRODUCCIÓN
