"""
Dependencias Reutilizables de FastAPI para Seguridad y Control de Acceso (RBAC).

"""

import logging
from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.database import get_db
from app.db.models import Usuario, RolEnum

logger = logging.getLogger(__name__)

# Configura el punto de anclaje para la documentación interactiva Swagger (/docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ══════════════════════════════════════════════════════════════════════════════
# 1. IDENTIFICACIÓN Y AUTENTICACIÓN 
# ══════════════════════════════════════════════════════════════════════════════

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Interintercepta la petición, extrae y valida el JWT, y provee el usuario activo.
    
    Raises:
        HTTPException 401: Si el token expiró, está corrupto o el usuario fue eliminado.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado. Por favor, inicia sesión nuevamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. Decodificación criptográfica del token
    payload = decode_token(token)
    if not payload:
        # Registramos el evento de advertencia de forma interna para auditorías
        logger.warning("[Deps Auth] Intento de acceso con firma de token alterada o caducada.")
        raise credentials_exception

    # 2. Extracción del sujeto (Subject Claim)
    email: str = payload.get("sub")
    if not email:
        logger.warning("[Deps Auth] Payload de token válido pero carece del campo 'sub'.")
        raise credentials_exception

    # 3. Localización y verificación del estado del usuario en la base de datos
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user:
        logger.error("[Deps Auth] Token legítimo pero el usuario '%s' ya no existe en la base de datos.", email)
        raise credentials_exception

    return user


# ══════════════════════════════════════════════════════════════════════════════
# 2. CONTROL DE ACCESO DINÁMICO 
# ══════════════════════════════════════════════════════════════════════════════

class RoleChecker:
    """
    Garantiza el cumplimiento de políticas de acceso basadas en roles de usuario.
    
    Aplica OCP: Permite validar múltiples roles permitidos sin reescribir
    funciones repetitivas o rígidas.
    """
    
    def __init__(self, allowed_roles: List[RolEnum]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Usuario = Depends(get_current_user)) -> Usuario:
        """Determina dinámicamente si el rol del usuario satisface la política de la ruta."""
        if current_user.rol not in self.allowed_roles:
            logger.warning(
                "[Deps RBAC] Acceso denegado. Usuario ID %d (Rol: %s) intentó invocar ruta restringida.",
                current_user.id, current_user.rol
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No posees los privilegios requeridos para ejecutar esta acción.",
            )
        return current_user


# ══════════════════════════════════════════════════════════════════════════════
# 3. INTERFACES PREPARADAS 
# ══════════════════════════════════════════════════════════════════════════════

# Mantiene compatibilidad absoluta con tus rutas existentes (como /api/vehiculos)
require_admin = RoleChecker(allowed_roles=[RolEnum.admin])

