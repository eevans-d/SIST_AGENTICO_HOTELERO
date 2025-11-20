# PLAN DE CONFIGURACIÓN ADICIONAL PARA "SIST_AGENTICO_HOTELERO" (v2.0 - Revisado)

**Versión:** 2.0
**Fecha:** 2025-11-14
**Objetivo:** Servir como guía técnica para configurar los servicios de Autenticación y Storage, incorporando recomendaciones de seguridad.

---

## FASE 2: CONFIGURACIÓN DE AUTENTICACIÓN Y AUTORIZACIÓN

### 2.1. Navegar a la Sección de Autenticación
*   En el panel del proyecto Supabase, ve a la sección **"Authentication"**.

### 2.2. Configurar Proveedores (Providers)
*   En el menú lateral, selecciona **"Providers"**.
*   **Habilitar "Email":** Activa el proveedor `Email`. Asegúrate de que la opción **"Confirm email"** esté marcada.
*   **(Opcional) Habilitar "Google":** Activa el proveedor `Google` e ingresa el `Client ID` y `Client Secret` si los tienes.

### 2.3. Revisar Plantillas de Correo
*   En el menú lateral, ve a **"Templates"**. Las plantillas por defecto son suficientes para empezar.

### 2.4. Fortalecer la Seguridad de Autenticación (Recomendado)
1.  Navega a **"Authentication" > "Settings"**.
2.  **Habilitar MFA:** Considera activar la Autenticación de Múltiples Factores (MFA) para una capa extra de seguridad en producción.
3.  **Configurar Plantilla de Contraseña:** En la sección "Password template", aumenta la longitud mínima de la contraseña a 10 o 12 caracteres.
4.  **Deshabilitar "Enable sign-ups":** Si el registro de usuarios es solo por invitación o gestionado por un administrador, deshabilita el registro público para mayor seguridad.

---

## FASE 4: CONFIGURACIÓN DE STORAGE

### 4.1. Creación de Buckets

1.  **Navegar a la Sección de Storage:**
    *   En el panel del proyecto Supabase, ve a la sección **"Storage"**.

2.  **Crear Bucket para Imágenes de Habitaciones:**
    *   **Nombre:** `habitaciones_imagenes`
    *   **Acceso Público:** **Activado**.

3.  **Crear Bucket para Avatares de Perfil:**
    *   **Nombre:** `avatars`
    *   **Acceso Público:** **Desactivado**.

### 4.2. Aplicar Políticas de Seguridad para Storage (SQL)

1.  **Navegar al Editor de SQL:**
    *   Ve a la sección **"SQL Editor"** y ejecuta las siguientes sentencias.

```sql
-- POLÍTICAS PARA EL BUCKET 'avatars'

-- Permite que CUALQUIERA pueda ver los avatares. Es una política común para fotos de perfil públicas.
CREATE POLICY "Public read access for avatars"
ON storage.objects FOR SELECT
USING ( bucket_id = 'avatars' );

-- Permite que un usuario autenticado pueda subir su propio avatar.
-- La política asume que la app sube el archivo a una carpeta con el nombre del user_id.
-- Ejemplo: avatars/00000000-0000-0000-0000-000000000000/avatar.png
CREATE POLICY "User can upload their own avatar"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK ( bucket_id = 'avatars' AND auth.uid() = (storage.foldername(name))[1]::uuid );

-- Permite que un usuario autenticado pueda actualizar su propio avatar.
CREATE POLICY "User can update their own avatar"
ON storage.objects FOR UPDATE
TO authenticated
USING ( bucket_id = 'avatars' AND auth.uid() = (storage.foldername(name))[1]::uuid );

-- Permite que un usuario autenticado pueda borrar su propio avatar.
CREATE POLICY "User can delete their own avatar"
ON storage.objects FOR DELETE
TO authenticated
USING ( bucket_id = 'avatars' AND auth.uid() = (storage.foldername(name))[1]::uuid );
```