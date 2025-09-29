from typing import Callable, Any
from fastapi import Request
from functools import wraps
import inspect
from ..core.settings import settings


def limit(rule: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorador dinámico que aplica rate limiting usando el limiter en request.app.state.limiter.
    Permite que las pruebas reemplacen el limiter a memoria sin acoplarse a una instancia global.
    """

    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def _wrapped(*args: Any, **kwargs: Any):
            # En modo debug, omitir rate limiting para facilitar desarrollo/tests
            if getattr(settings, "debug", False):
                return await func(*args, **kwargs)
            # Intentar extraer el Request de args/kwargs
            request: Request | None = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                # Si no hay request, ejecutar sin limit (fallback seguro)
                return await func(*args, **kwargs)

            limiter = getattr(request.app.state, "limiter", None)
            if limiter is None:
                return await func(*args, **kwargs)

            # Construir el decorador real en tiempo de ejecución y aplicarlo
            decorated = limiter.limit(rule)(func)
            return await decorated(*args, **kwargs)

        # Preservar firma original para FastAPI
        try:
            _wrapped.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
        except Exception:
            pass
        return _wrapped

    return _decorator
