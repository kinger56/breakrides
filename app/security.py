"""Password hashing and login tokens, using only Python's standard library.

Passwords: never stored, only a salted scrypt hash. scrypt is deliberately
slow and memory-hungry, so guessing passwords from a stolen hash is costly.
Each password gets its own random salt, so two users with the same
password still get different hashes.

Login tokens: a long random string goes into the browser's cookie. We store
only its SHA-256 hash. Tokens are random (not passwords people reuse), so a
fast hash is fine here.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

# scrypt cost settings (OWASP-recommended minimum: N=2^17 is stronger but
# slower; 2^14 keeps tests fast while still being expensive to brute-force).
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p)
    )
    # compare_digest takes the same time whether the first or last byte
    # differs, so attackers can't learn the hash by timing responses.
    return hmac.compare_digest(digest.hex(), digest_hex)


def new_email_code() -> str:
    """6 random digits, like "042917". Leading zeros are kept."""
    return f"{secrets.randbelow(10**6):06d}"


def hash_email_code(user_id: int, code: str) -> str:
    # Mixing in the user id means the same code for two users hashes differently.
    return hashlib.sha256(f"{user_id}:{code}".encode()).hexdigest()


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
