"""
Módulo de Configuración de Infraestructura de Base de Datos (SQLAlchemy).

Aplica el Principio de Inversión de Dependencias (DIP) exponiendo un generador
de sesiones contextuales (Session-per-Request) integrado nativamente con el
sistema de Inyección de Dependencias de FastAPI.
"""

import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN DEL MOTOR 
# ══════════════════════════════════════════════════════════════════════════════

def _get_engine_connect_args(database_url: str) -> dict:
    """
    Construye los argumentos específicos de conexión basados en el dialecto de la BD.
    
    Aplica encapsulamiento: aísla la regla especial de hilos que requiere SQLite.
    """
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


# Inicialización única del motor de conexión y su fábrica de sesiones (Factory Pattern)
engine = create_engine(
    settings.database_url, 
    connect_args=_get_engine_connect_args(settings.database_url)
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)


# ══════════════════════════════════════════════════════════════════════════════
# 2. MODELO BASE DECLARATIVO 
# ══════════════════════════════════════════════════════════════════════════════

class Base(DeclarativeBase):
    """
    Clase Base Declarativa unificada para la asignación de esquemas ORM.
    
    Todos los modelos del sistema (User, Vehiculo, etc.) deben heredar de ella
    para ser mapeados correctamente en la base de datos relacional.
    """
    pass


# ══════════════════════════════════════════════════════════════════════════════
# 3. GESTIÓN DE SESIONES 
# ══════════════════════════════════════════════════════════════════════════════

def get_db() -> Generator[Session, None, None]:
    """
    Inyector de Dependencia Contextual de FastAPI.
    
    Garantiza el patrón 'Session-per-Request': abre una sesión aislada por cada 
    petición HTTP entrante y asegura su cierre mandatorio en el servidor una vez 
    que el ciclo de la petición finaliza.
    
    Yields:
        Session: Sesión transaccional activa de SQLAlchemy.
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception as exc:
        logger.error("[Database] Error detectado en la transacción de la sesión: %s", str(exc))
        raise exc
    finally:
        db.close()