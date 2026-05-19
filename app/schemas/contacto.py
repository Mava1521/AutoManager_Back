"""
Esquemas de Validación y Serialización Pydantic para el Módulo de Soporte.

"""

from pydantic import BaseModel, EmailStr, Field, field_validator


# ══════════════════════════════════════════════════════════════════════════════
# DATA TRANSFER OBJECTS 
# ══════════════════════════════════════════════════════════════════════════════

class ContactRequest(BaseModel):
    """Contrato de entrada para los tickets emitidos desde el AutoBot de soporte."""
    
    sender_email: EmailStr
    
    # str_strip=True remueve automáticamente espacios en blanco innecesarios al inicio y final
    subject: str = Field(..., min_length=1, max_length=150, str_strip=True)
    message: str = Field(..., min_length=1, max_length=2000, str_strip=True)

    @field_validator("subject", "message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        """Garantiza de forma estricta que los textos no contengan únicamente espacios vacíos."""
        if not value or not value.strip():
            raise ValueError("El campo no puede estar vacío o contener únicamente espacios.")
        return value


class ContactResponse(BaseModel):
    """Estructura de confirmación de despacho de tickets hacia el cliente."""
    
    ok: bool
    detail: str

    model_config = {
        "frozen": True  # Optimiza el rendimiento de serialización haciéndolo inmutable
    }