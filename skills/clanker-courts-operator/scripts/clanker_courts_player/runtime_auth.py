from __future__ import annotations

import hashlib
import hmac
import secrets
from pathlib import Path


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str, *, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", token.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_token(token: str, encoded: str) -> bool:
    try:
        algorithm, salt, digest = encoded.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    return hmac.compare_digest(token_hash(token, salt=salt), f"{algorithm}${salt}${digest}")


def write_secret_file(path: Path, token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = "x" if not path.exists() else "w"
    with path.open(flags, encoding="utf-8") as handle:
        handle.write(token)
        handle.write("\n")
    path.chmod(0o600)


def read_secret_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()
