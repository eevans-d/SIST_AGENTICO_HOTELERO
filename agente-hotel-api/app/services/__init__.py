"""Servicios del dominio.

- Este paquete no debe forzar importaciones pesadas u opcionales en import time.
- Evitar efectos secundarios que rompan tests cuando dependencias opcionales no estén instaladas.

Nota: `qr_service` depende de `qrcode` (opcional). Para no romper la importación
de `app` en entornos sin esa dependencia, el import se hace de manera perezosa y tolerante.
"""

# Exponer qr_service si está disponible (evitar fallo duro cuando qrcode no esté instalado)
try:
	from . import qr_service  # noqa: F401
except Exception:
	# Dejar silencioso: tests que lo requieran pueden manejar la ausencia o mockearlo
	qr_service = None  # type: ignore[assignment]

