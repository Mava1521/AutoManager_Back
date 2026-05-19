"""
Endpoints de Autenticación y Control de Accesos (RBAC).

"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.core.email import send_recovery_email
from app.db.database import get_db
from app.db.models import Usuario, RolEnum, PasswordResetToken
from app.schemas.auth import (
    RegisterRequest,
    LoginResponse,
    RecoveryRequest,
    RecoveryResponse,
    ResetPasswordRequest,
    UserOut,
)
from app.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

_RESET_TOKEN_EXPIRE_MINUTES = 30


# ══════════════════════════════════════════════════════════════════════════════
# SERVICIO DE SOPORTE INTERNO 
# ══════════════════════════════════════════════════════════════════════════════

class AuthService:
    """Encapsula las reglas de negocio transaccionales del módulo de autenticación."""
    
    @staticmethod
    def invalidate_and_create_reset_token(db: Session, user_id: int) -> str:
        """Garantiza la unicidad y creación de un token seguro de recuperación."""
        # 1. Eliminar de forma segura registros antiguos (Idempotencia)
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()
        
        # 2. Construir el nuevo token seguro
        raw_token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(minutes=_RESET_TOKEN_EXPIRE_MINUTES)
        
        reset_entry = PasswordResetToken(
            user_id=user_id,
            token=raw_token,
            expires_at=expires,
            used=False
        )
        db.add(reset_entry)
        db.commit()
        return raw_token

    @staticmethod
    def is_token_expired(expires_at: datetime) -> bool:
        """Determina con precisión geográfica si un token ha caducado."""
        expiry = expires_at.replace(tzinfo=timezone.utc) if expires_at.tzinfo is None else expires_at
        return expiry < datetime.now(timezone.utc)


# ══════════════════════════════════════════════════════════════════════════════
# CONTROLADORES DE RUTA 
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/login", response_model=LoginResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Autentica credenciales de usuario mediante protocolo OAuth2 y despacha JWT."""
    user = db.query(Usuario).filter(Usuario.email == form.username).first()

    if not user or not verify_password(form.password, user.password):
        logger.warning("[Auth] Intento fallido de inicio de sesión para: %s", form.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # El Middleware se encargará de inyectar automáticamente el log de auditoría
    token = create_access_token({"sub": user.email, "role": user.rol})
    return LoginResponse(access_token=token, role=user.rol, nombre=user.nombre)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserOut:
    """Registra una nueva cuenta de usuario en el sistema con rol base (viewer)."""
    if db.query(Usuario).filter(Usuario.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cuenta con ese correo electrónico.",
        )

    new_user = Usuario(
        nombre=payload.nombre,
        apellido=payload.apellido,
        email=payload.email,
        password=hash_password(payload.password),
        rol=RolEnum.viewer,
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as exc:
        db.rollback()
        logger.error("[Auth] Error al registrar usuario en la base de datos: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo completar el registro del usuario."
        )

    logger.info("[Auth] Cuenta creada exitosamente: id=%d", new_user.id)
    return new_user


@router.post("/recovery", response_model=RecoveryResponse)
def request_recovery(
    payload: RecoveryRequest,
    db: Session = Depends(get_db),
) -> RecoveryResponse:
    """
    Inicia el flujo seguro de recuperación de credenciales.
    
    Estrategia de Seguridad contra Ataques de Enumeración:
    Siempre responde HTTP 200 para mitigar el descubrimiento malicioso de cuentas activas.
    """
    user = db.query(Usuario).filter(Usuario.email == payload.email).first()

    if user:
        try:
            # Delegamos la orquestación lógica al servicio de dominio
            reset_token = AuthService.invalidate_and_create_reset_token(db, user_id=user.id)
            
            # Despacho de correo electrónico transaccional
            send_recovery_email(
                to_email=user.email,
                to_name=user.nombre,
                reset_token=reset_token,
            )
            logger.info("[Auth] Solicitud de recuperación procesada para user_id=%d", user.id)
        except Exception as exc:
            # Fallo seguro controlado: no bloquea la respuesta al cliente legítimo
            logger.error("[Auth] Fallo de infraestructura enviando correo a user_id=%d: %s", user.id, str(exc))

    return RecoveryResponse(
        message="Si ese correo está registrado, recibirás las instrucciones en breve."
    )


@router.post("/reset-password", response_model=RecoveryResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> RecoveryResponse:
    """Valida la legitimidad del token efímero y actualiza la contraseña del usuario."""
    reset_entry = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == payload.token,
        PasswordResetToken.used == False
    ).first()

    if not reset_entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido o utilizado.")

    if AuthService.is_token_expired(reset_entry.expires_at):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El token ha expirado.")

    user = db.query(Usuario).filter(Usuario.id == reset_entry.user_id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario asociado no encontrado.")

    try:
        user.password = hash_password(payload.new_password)
        reset_entry.used = True
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("[Auth] Error actualizando credenciales para user_id=%d: %s", user.id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno procesando el cambio de contraseña."
        )

    logger.info("[Auth] Credenciales actualizadas correctamente para user_id=%d", user.id)
    return RecoveryResponse(message="Contraseña actualizada correctamente.")


@router.get("/me", response_model=UserOut)
def get_me(current_user: Usuario = Depends(get_current_user)) -> UserOut:
    """Retorna de manera segura la identidad del usuario actualmente autenticado en la sesión."""
    return current_user