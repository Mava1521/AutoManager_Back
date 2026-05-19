"""
Módulo de Servicios de Seguridad y Criptografía.

"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 1. SERVICIO DE HASHING (Single Responsibility Principle)
# ══════════════════════════════════════════════════════════════════════════════

class PasswordHasher:
    """
    Encargado exclusivo del ciclo de vida y verificación de contraseñas.
    """
    
    def __init__(self):
        # 1. Definimos el contexto como atributo de la instancia (self._context)
        # 2. Agregamos bcrypt__ident="2b" para evitar el error de verificación de bugs en Render
        self._context = CryptContext(
            schemes=["bcrypt"], 
            deprecated="auto",
            bcrypt__ident="2b"
        )

    def hash(self, plain_password: str) -> str:
        """Transforma una contraseña en texto plano en un hash seguro e irreversible."""
        if not plain_password:
            raise ValueError("La contraseña a procesar no puede estar vacía.")
        # Truncamos a 72 caracteres para evitar el ValueError de bcrypt
        return self._context.hash(plain_password[:72])

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Compara de forma segura una contraseña en texto plano con su hash."""
        if not plain_password or not hashed_password:
            return False
        try:
            # Truncamos también aquí al verificar
            return self._context.verify(plain_password[:72], hashed_password)
        except Exception as exc:
            logger.error("[Security] Error inesperado verificando hash: %s", str(exc))
            return False

# ══════════════════════════════════════════════════════════════════════════════
# 2. SERVICIO DE TOKENS (Open/Closed Principle & DIP)
# ══════════════════════════════════════════════════════════════════════════════

class TokenProvider:
    """
    Gestiona la emisión, firma y validación de tokens de acceso JWT.
    
    Abstrae las claves y algoritmos definidos en la configuración central.
    """
    
    def __init__(self):
        self._secret_key = settings.secret_key
        self._algorithm = settings.algorithm
        self._default_expiry = settings.access_token_expire_minutes

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Genera un JSON Web Token firmado con firma criptográfica simétrica.
        
        Args:
            data: Payload base, debe incluir obligatoriamente {"sub": email, "role": rol}.
            expires_delta: Tiempo de expiración personalizado opcional.
        """
        payload = data.copy()
        
        # Uso estricto de zonas horarias (Aware UTC) para evitar fallos de desfase en servidores nube
        duration = expires_delta or timedelta(minutes=self._default_expiry)
        expiration_time = datetime.now(timezone.utc) + duration
        
        payload.update({"exp": expiration_time})
        
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decodifica, lee y valida la firma y vigencia de un JWT.
        
        Returns:
            Dict: El payload original si el token es íntegro y vigente.
            None: Si el token expiró, fue alterado o está malformado.
        """
        try:
            return jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except JWTError as exc:
            # Logueo silencioso de advertencia para auditorías sin interrumpir el flujo
            logger.warning("[Security Auth] Intento de acceso con token inválido o expirado.")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# 3. EXPOSICIÓN RETROCOMPATIBLE (Interface Preservation)
# ══════════════════════════════════════════════════════════════════════════════

# Instancias únicas del servicio (Patrón Singleton implícito)
_hasher = PasswordHasher()
_token_provider = TokenProvider()

# Mapeo de firmas idénticas para garantizar que ningún router o middleware se rompa
def hash_password(plain: str) -> str:
    return _hasher.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _hasher.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return _token_provider.create_access_token(data, expires_delta)

def decode_token(token: str) -> Optional[dict]:
    return _token_provider.decode_token(token)