# app/db/models.py
"""
Módulo de Modelos de Datos del Sistema (Esquemas ORM).

Define la estructura de las tablas relacionales de la base de datos de AutoManager.
Aplica principios de encapsulamiento e integridad referencial mediante claves
foráneas y relaciones orientadas a objetos.
"""

import enum
from sqlalchemy import Column, Integer, String, Enum, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


# ══════════════════════════════════════════════════════════════════════════════
# ENUMERACIONES 
# ══════════════════════════════════════════════════════════════════════════════

class RolEnum(str, enum.Enum):
    """Define los roles de acceso autorizados dentro del ecosistema."""
    admin = "admin"
    viewer = "viewer"


class StatusEnum(str, enum.Enum):
    """Representa el estado del ciclo de vida en el flujo de un vehículo."""
    PENDIENTE = "Pendiente"      
    EN_REVISION = "En Revisión"     
    APROBADO = "Aprobado"         
    RECHAZADO = "Rechazado"       


# ══════════════════════════════════════════════════════════════════════════════
# MODELOS ORM 
# ══════════════════════════════════════════════════════════════════════════════

class Usuario(Base):
    """
    Representa a los usuarios autenticables del sistema AutoManager.
    
    Posee una relación uno-a-muchos hacia sus tokens de restablecimiento.
    """
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(80), nullable=False)
    apellido = Column(String(80), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    rol = Column(Enum(RolEnum), default=RolEnum.viewer, nullable=False)

    # 🔗 Relación (SOLID - Navegabilidad orientada a objetos)
    # cascade="all, delete-orphan" asegura que si se borra un usuario, se limpian sus tokens automáticamente
    reset_tokens = relationship(
        "PasswordResetToken", 
        back_populates="usuario", 
        cascade="all, delete-orphan"
    )


class Vehiculo(Base):
    """
    Entidad central del negocio. Gestiona la información de los vehículos.
    
    Utilizado en el panel administrativo por administradores y auditores.
    """
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    marca = Column(String(80), nullable=False)
    sucursal = Column(String(120), nullable=False)
    aspirante = Column(String(160), nullable=False)
    status = Column(Enum(StatusEnum), default=StatusEnum.PENDIENTE, nullable=False)


class PasswordResetToken(Base):
    """
    Entidad de soporte de seguridad.
    
    Almacena tokens efímeros firmados criptográficamente para el flujo de
    recuperación de contraseña de usuarios no autenticados.
    """
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(100), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)

    # 🔗 Relación Inversa (Navegabilidad bidireccional)
    usuario = relationship("Usuario", back_populates="reset_tokens")