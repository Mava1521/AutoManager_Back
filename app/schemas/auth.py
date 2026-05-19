"""
Esquemas de Validación y Serialización Pydantic para Autenticación.

"""

from pydantic import BaseModel, EmailStr, Field

# ── Importación del Enum de Dominio (Evita duplicación - DRY) ──
from app.db.models import RolEnum


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS 
# ══════════════════════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    """Contrato de datos requerido de forma mandatoria para la creación de cuentas."""
    
    # str_strip=True limpia automáticamente espacios accidentales al inicio y final
    nombre: str = Field(..., min_length=1, max_length=80, str_strip=True)
    apellido: str = Field(..., min_length=1, max_length=80, str_strip=True)
    email: EmailStr
    password: str = Field(
        ..., 
        min_length=8, 
        description="Contraseña de acceso. Se requiere una longitud mínima de 8 caracteres."
    )


class RecoveryRequest(BaseModel):
    """Estructura de entrada para solicitudes seguras de restablecimiento."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Payload para consolidar el cambio de contraseña mediante token efímero."""
    token: str = Field(..., min_length=1, description="Token criptográfico enviado por correo.")
    new_password: str = Field(..., min_length=8, description="Nueva credencial de acceso segura.")


# ══════════════════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS 
# ══════════════════════════════════════════════════════════════════════════════

class LoginResponse(BaseModel):
    """Contrato de respuesta exitosa tras una autenticación OAuth2 estándar."""
    access_token: str
    token_type: str = "bearer"
    role: RolEnum
    nombre: str


class RecoveryResponse(BaseModel):
    """Respuesta unificada y agnóstica para los endpoints de recuperación."""
    message: str


class UserOut(BaseModel):
    """
    Perfil público del usuario serializado de forma segura.
    
    Garantiza el aislamiento de seguridad bloqueando la salida de hashes de
    contraseñas hacia el cliente frontend.
    """
    id: int
    nombre: str
    apellido: str
    email: EmailStr  # Tipado estricto coincidente con la entrada
    rol: RolEnum

    # Configuración nativa de Pydantic V2 para mapear objetos ORM (SQLAlchemy) de forma automática
    model_config = {
        "from_attributes": True,
        "frozen": True  # Hace que el esquema de salida sea inmutable y más rápido en memoria
    }