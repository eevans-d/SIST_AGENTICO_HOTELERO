# PLAN DE IMPLEMENTACIÓN DE EDGE FUNCTIONS PARA "SIST_AGENTICO_HOTELERO" (v2.0 - Revisado)

**Versión:** 2.0
**Fecha:** 2025-11-14
**Objetivo:** Proveer una arquitectura robusta y segura para la lógica de negocio, evitando condiciones de carrera mediante el uso de Funciones de Base de Datos (RPC).

---

## FASE 3: DESARROLLO DE FUNCIONALIDAD (ARQUITECTURA MEJORADA)

### 3.1. Crear Función de Base de Datos Atómica (RPC)

**Propósito:** Centralizar la lógica de creación de reservas en una única función de base de datos que se ejecuta de forma atómica, eliminando el riesgo de `race conditions` (dobles reservas).

#### Instrucciones:
Ejecuta el siguiente código en el **"SQL Editor"** de tu panel de Supabase.

```sql
-- Función atómica para crear una reserva de forma segura
CREATE OR REPLACE FUNCTION crear_reserva_segura(
    p_user_id UUID,
    p_habitacion_id BIGINT,
    p_check_in_date DATE,
    p_check_out_date DATE,
    p_number_of_guests INT
)
RETURNS JSON -- Devuelve la reserva creada o un objeto de error
LANGUAGE plpgsql
AS $$
DECLARE
    v_habitacion RECORD;
    v_overlapping_count INT;
    v_total_price NUMERIC;
    v_nights INT;
    v_new_reserva JSON;
BEGIN
    -- Bloquear la fila de la habitación para evitar que otras transacciones la modifiquen
    SELECT price_per_night, capacity INTO v_habitacion FROM public.habitaciones WHERE id = p_habitacion_id FOR UPDATE;

    IF NOT FOUND THEN
        RETURN json_build_object('error', 'Habitación no encontrada');
    END IF;

    IF p_number_of_guests > v_habitacion.capacity THEN
        RETURN json_build_object('error', 'La capacidad de la habitación ha sido excedida');
    END IF;

    -- Verificar solapamiento de fechas de forma segura
    SELECT count(*) INTO v_overlapping_count
    FROM public.reservas
    WHERE habitacion_id = p_habitacion_id
      AND status IN ('confirmada', 'pendiente')
      AND daterange(check_in_date, check_out_date, '[]') && daterange(p_check_in_date, p_check_out_date, '[]');

    IF v_overlapping_count > 0 THEN
        RETURN json_build_object('error', 'La habitación no está disponible para las fechas seleccionadas');
    END IF;

    -- Calcular precio
    v_nights := p_check_out_date - p_check_in_date;
    v_total_price := v_nights * v_habitacion.price_per_night;

    -- Insertar la reserva
    INSERT INTO public.reservas (user_id, habitacion_id, check_in_date, check_out_date, number_of_guests, total_price, status)
    VALUES (p_user_id, p_habitacion_id, p_check_in_date, p_check_out_date, p_number_of_guests, v_total_price, 'confirmada')
    RETURNING to_json(reservas.*) INTO v_new_reserva;

    RETURN v_new_reserva;
END;
$$;
```

### 3.2. Código de la Edge Function (Simplificado)

**Propósito:** La Edge Function ahora actúa como un proxy seguro que valida al usuario y pasa la solicitud a la función de base de datos `crear_reserva_segura`.

#### Instrucciones:
Asegúrate de que el archivo `supabase/functions/procesar-reserva/index.ts` tenga el siguiente contenido.

```typescript
// File: supabase/functions/procesar-reserva/index.ts (VERSIÓN MEJORADA)

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.0.0";
import { corsHeaders } from "../_shared/cors.ts";

serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { habitacion_id, check_in_date, check_out_date, number_of_guests } = await req.json();

    const supabaseClient = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );
    
    const { data: { user } } = await supabaseClient.auth.getUser(req.headers.get("Authorization")!.replace("Bearer ", ""));
    if (!user) throw new Error("Usuario no autenticado.");

    // Llamar a la función RPC atómica, que ahora contiene toda la lógica de negocio
    const { data: result, error: rpcError } = await supabaseClient.rpc('crear_reserva_segura', {
      p_user_id: user.id,
      p_habitacion_id: habitacion_id,
      p_check_in_date: check_in_date,
      p_check_out_date: check_out_date,
      p_number_of_guests: number_of_guests
    });

    if (rpcError) throw rpcError;

    // La función RPC devuelve un objeto con una propiedad 'error' si algo falló
    if (result.error) {
      return new Response(JSON.stringify({ error: result.error }), {
        status: 409, // 409 Conflict (ej: habitación no disponible)
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Si todo fue exitoso, devuelve la nueva reserva
    return new Response(JSON.stringify(result), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      status: 201, // 201 Created
    });

  } catch (error) {
    // Captura errores de autenticación, JSON malformado, etc.
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      status: 400,
    });
  }
});
```

### 3.3. Despliegue de la Función
El proceso de despliegue no cambia. Usa la Supabase CLI:
`supabase functions deploy procesar-reserva --no-verify-jwt`