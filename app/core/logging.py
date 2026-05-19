"""
Módulo de Monitoreo e Intercepción de Tráfico HTTP (Logging Middleware).
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("automanager")


def setup_logging() -> None:
    """
    Configura de manera segura el formato y los manejadores de los logs del sistema.
    """
    # Evita reconfigurar si ya existen manejadores activos
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        # Evita que los mensajes se dupliquen subiendo al logger raíz
        logger.propagate = False

class EmailRenderer:
    """
    Clase para manejar el formateo de correos electrónicos.
    Cumple con el principio de responsabilidad única (SRP).
    """
    @staticmethod
    def mask_email(email: str) -> str:
        if not email or "@" not in email:
            return email
        user, domain = email.split("@")
        if len(user) <= 2:
            return f"{user[0]}***@{domain}"
        return f"{user[:2]}***@{domain}"

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Intercepta las peticiones HTTP entrantes para auditar el rendimiento y acceso.

    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Garantiza que el sistema de logs esté preparado
        setup_logging()

    def _extract_user_identity(self, request: Request) -> str:
        """
        Extrae de forma segura los metadatos de identidad adjuntos en la request.
        
        No decodifica el JWT directamente aquí para evitar duplicación de lógica 
        y vulnerabilidades de seguridad; en su lugar, aprovecha el estado interno 
        inyectado por los esquemas de seguridad de FastAPI o lee de forma pasiva.
        """
        # 1. Intenta leer si un esquema de seguridad previo ya autenticó al usuario
        if hasattr(request.state, "user") and request.state.user:
            user = request.state.user
            sub = getattr(user, "email", getattr(user, "sub", "?"))
            role = getattr(user, "role", "?")
            return f"usuario={sub} rol={role}"
            
        # 2. Caída pasiva si el token solo viaja en los headers y aún no se procesa
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Nota: Retornamos presencia pasiva para evitar romper el flujo si el token es inválido
            return "usuario=autenticado (JWT Presente)"
            
        return "anónimo"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # Procesar la solicitud aguas abajo en la tubería (Pipeline) de FastAPI
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            # Asegura registrar la falla de rendimiento incluso si la app explota internamente (500)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            user_info = self._extract_user_identity(request)
            logger.error(
                "[%s] %s → CRASH (%.1fms) | %s | Error: %s",
                request.method, request.url.path, elapsed_ms, user_info, str(exc)
            )
            raise exc

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        user_info = self._extract_user_identity(request)

        # Registro formal de auditoría exitosa o controlada (2xx, 3xx, 4xx)
        logger.info(
            "[%s] %s → %s (%.1fms) | %s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            user_info,
        )

        return response