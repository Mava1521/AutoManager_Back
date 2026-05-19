"""
Esquemas de Validación y Serialización Pydantic para Vehículos.

"""

from typing import Optional
from pydantic import BaseModel, Field

# ── Importación del Enum de Dominio (Evita duplicación - DRY) ──
from app.db.models import StatusEnum


# ══════════════════════════════════════════════════════════════════════════════
# BASE DATA TRANSFER OBJECTS 
# ══════════════════════════════════════════════════════════════════════════════

class VehiculoBase(BaseModel):
    """Estructura base compartida para la transferencia de datos de vehículos."""
    
    # str_strip=True remueve espacios accidentales antes y después del texto
    marca: str = Field(..., min_length=1, max_length=80, str_strip=True)
    sucursal: str = Field(..., min_length=1, max_length=120, str_strip=True)
    aspirante: str = Field(..., min_length=1, max_length=160, str_strip=True)
    status: StatusEnum = Field(default=StatusEnum.PENDIENTE)


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS 
# ══════════════════════════════════════════════════════════════════════════════

class VehiculoCreate(VehiculoBase):
    """Payload estricto requerido para la creación de un nuevo vehículo."""
    pass


class VehiculoUpdate(BaseModel):
    """
    Payload flexible para la modificación parcial de un vehículo (PATCH/PUT).
    
    Permite enviar únicamente los campos que se desean alterar en el sistema.
    """
    marca: Optional[str] = Field(None, min_length=1, max_length=80, str_strip=True)
    sucursal: Optional[str] = Field(None, min_length=1, max_length=120, str_strip=True)
    aspirante: Optional[str] = Field(None, min_length=1, max_length=160, str_strip=True)
    status: Optional[StatusEnum] = Field(None)


# ══════════════════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS 
# ══════════════════════════════════════════════════════════════════════════════

class VehiculoOut(VehiculoBase):
    """
    Esquema de salida estructurado para la exposición pública de vehículos.
    
    Incluye el identificador único asignado de forma autoincremental.
    """
    id: int

    # Configuración nativa de Pydantic V2 para el mapeo automático de modelos de SQLAlchemy
    model_config = {
        "from_attributes": True,
        "frozen": True  # Hace el objeto inmutable en memoria optimizando la serialización
    }