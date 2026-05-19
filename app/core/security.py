from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# 1. SERVICIO DE HASHING
# ══════════════════════════════════════════════════════════════════════════════

class PasswordHasher:
    def __init__(self):
        self._context = CryptContext(
            schemes=["bcrypt"], 
            deprecated="auto",
            bcrypt__ident="2b"
        )

    def hash(self, plain_password: str) -> str:
        if not plain_password:
            raise ValueError("La contraseña no puede estar vacía.")
        return self._context.hash(plain_password[:72])

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        if not plain_password or not hashed_password:
            return False
        try:
            return self._context.verify(plain_password[:72], hashed_password)
        except Exception as exc:
            logger.error("[Security] Error verificando hash: %s", str(exc))
            return False

# ══════════════════════════════════════════════════════════════════════════════
# 2. SERVICIO DE TOKENS (Corregido: sin CryptContext innecesario)
# ══════════════════════════════════════════════════════════════════════════════

class TokenProvider:
    def __init__(self):
        self._secret_key = settings.secret_key
        self._algorithm = settings.algorithm
        self._default_expiry = settings.access_token_expire_minutes

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        payload = data.copy()
        duration = expires_delta or timedelta(minutes=self._default_expiry)
        expiration_time = datetime.now(timezone.utc) + duration
        payload.update({"exp": expiration_time})
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except JWTError:
            logger.warning("[Security Auth] Token inválido o expirado.")
            return None

# ══════════════════════════════════════════════════════════════════════════════
# 3. EXPOSICIÓN RETROCOMPATIBLE
# ══════════════════════════════════════════════════════════════════════════════

_hasher = PasswordHasher()
_token_provider = TokenProvider()

def hash_password(plain: str) -> str: return _hasher.hash(plain)
def verify_password(plain: str, hashed: str) -> bool: return _hasher.verify(plain, hashed)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str: return _token_provider.create_access_token(data, expires_delta)
def decode_token(token: str) -> Optional[dict]: return _token_provider.decode_token(token)