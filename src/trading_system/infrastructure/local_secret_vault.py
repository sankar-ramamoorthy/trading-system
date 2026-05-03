"""Local encrypted secret vault for CLI credential storage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module
import json
import os
from pathlib import Path
from typing import Protocol

from cryptography.fernet import Fernet, InvalidToken


DEFAULT_VAULT_PATH = Path(".trading-system") / "keys.enc"
KEYRING_SERVICE = "trading-system.local-secret-vault"
KEYRING_USERNAME = "default"


class LocalSecretVaultError(ValueError):
    """Raised when the local secret vault cannot complete a requested operation."""


class KeyringBackend(Protocol):
    """Small keyring protocol used by the local vault."""

    def get_password(self, service_name: str, username: str) -> str | None:
        """Return a stored password or None."""
        ...

    def set_password(self, service_name: str, username: str, password: str) -> None:
        """Store a password."""
        ...


@dataclass(frozen=True)
class SecretEntry:
    """Metadata for a stored secret without exposing its value."""

    name: str
    updated_at: datetime


class LocalSecretVault:
    """Stores local CLI secrets in an encrypted file using an OS-keychain key."""

    def __init__(
        self,
        vault_path: Path | str = DEFAULT_VAULT_PATH,
        *,
        keyring_backend: KeyringBackend | None = None,
    ) -> None:
        self._vault_path = Path(vault_path)
        self._keyring = keyring_backend or _load_keyring()

    @property
    def vault_path(self) -> Path:
        """Return the encrypted vault file path."""
        return self._vault_path

    def set_secret(self, name: str, value: str) -> SecretEntry:
        """Store or replace one secret value."""
        secret_name = _normalize_secret_name(name)
        if not value:
            raise LocalSecretVaultError("Secret value is required.")

        data = self._read_or_empty(for_write=True)
        updated_at = datetime.now(UTC)
        data["secrets"][secret_name] = {
            "value": value,
            "updated_at": updated_at.isoformat(),
        }
        self._write(data)
        return SecretEntry(name=secret_name, updated_at=updated_at)

    def get_secret(self, name: str) -> str | None:
        """Return one secret value, or None when it is absent."""
        secret_name = _normalize_secret_name(name)
        data = self._read_or_empty(for_write=False)
        record = data["secrets"].get(secret_name)
        if record is None:
            return None
        value = record.get("value")
        if not isinstance(value, str):
            raise LocalSecretVaultError("Local secret vault is invalid.")
        return value

    def delete_secret(self, name: str) -> bool:
        """Delete one secret value and return whether it existed."""
        secret_name = _normalize_secret_name(name)
        data = self._read_or_empty(for_write=False)
        existed = secret_name in data["secrets"]
        if existed:
            del data["secrets"][secret_name]
            self._write(data)
        return existed

    def list_secrets(self) -> list[SecretEntry]:
        """List stored secret names and metadata without secret values."""
        data = self._read_or_empty(for_write=False)
        entries = []
        for name, record in data["secrets"].items():
            updated_at = record.get("updated_at")
            if not isinstance(updated_at, str):
                raise LocalSecretVaultError("Local secret vault is invalid.")
            entries.append(
                SecretEntry(
                    name=name,
                    updated_at=datetime.fromisoformat(updated_at),
                )
            )
        return sorted(entries, key=lambda entry: entry.name)

    def rotate_master_key(self) -> int:
        """Re-encrypt the vault with a new key and return the stored secret count."""
        data = self._read_or_empty(for_write=True)
        self._set_master_key(_new_key())
        self._write(data)
        return len(data["secrets"])

    def _read_or_empty(self, *, for_write: bool) -> dict:
        if not self._vault_path.exists():
            if for_write:
                self._ensure_master_key()
            return {"version": 1, "secrets": {}}

        key = self._master_key()
        if key is None:
            raise LocalSecretVaultError(
                "Local secret vault master key is missing from the OS keychain."
            )
        try:
            raw = Fernet(key.encode("utf-8")).decrypt(self._vault_path.read_bytes())
        except InvalidToken as exc:
            raise LocalSecretVaultError("Local secret vault could not be decrypted.") from exc
        except OSError as exc:
            raise LocalSecretVaultError("Local secret vault could not be read.") from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LocalSecretVaultError("Local secret vault is invalid.") from exc

        if (
            not isinstance(data, dict)
            or data.get("version") != 1
            or not isinstance(data.get("secrets"), dict)
        ):
            raise LocalSecretVaultError("Local secret vault is invalid.")
        return data

    def _write(self, data: dict) -> None:
        key = self._ensure_master_key()
        payload = json.dumps(data, sort_keys=True).encode("utf-8")
        encrypted = Fernet(key.encode("utf-8")).encrypt(payload)
        try:
            self._vault_path.parent.mkdir(parents=True, exist_ok=True)
            self._vault_path.write_bytes(encrypted)
        except OSError as exc:
            raise LocalSecretVaultError("Local secret vault could not be written.") from exc

    def _ensure_master_key(self) -> str:
        key = self._master_key()
        if key is not None:
            return key
        key = _new_key()
        self._set_master_key(key)
        return key

    def _master_key(self) -> str | None:
        try:
            return self._keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        except Exception as exc:  # pragma: no cover - backend specific
            raise LocalSecretVaultError("OS keychain is unavailable.") from exc

    def _set_master_key(self, key: str) -> None:
        try:
            self._keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, key)
        except Exception as exc:  # pragma: no cover - backend specific
            raise LocalSecretVaultError("OS keychain is unavailable.") from exc


def resolve_secret(
    name: str,
    *,
    vault: LocalSecretVault | None = None,
    environ: dict[str, str] | None = None,
) -> str | None:
    """Resolve a secret using vault-first, environment-fallback precedence."""
    secret_name = _normalize_secret_name(name)
    if vault is not None:
        value = vault.get_secret(secret_name)
        if value:
            return value
    elif DEFAULT_VAULT_PATH.exists():
        value = LocalSecretVault().get_secret(secret_name)
        if value:
            return value
    environment = os.environ if environ is None else environ
    fallback = environment.get(secret_name, "").strip()
    return fallback or None


def require_secret(
    name: str,
    *,
    vault: LocalSecretVault | None = None,
    environ: dict[str, str] | None = None,
) -> str:
    """Resolve a required secret or raise a clear error."""
    secret_name = _normalize_secret_name(name)
    value = resolve_secret(secret_name, vault=vault, environ=environ)
    if value is None:
        raise LocalSecretVaultError(f"{secret_name} is required.")
    return value


def _normalize_secret_name(name: str) -> str:
    normalized = name.strip().upper()
    if not normalized:
        raise LocalSecretVaultError("Secret name is required.")
    if any(char.isspace() for char in normalized):
        raise LocalSecretVaultError("Secret name must not contain whitespace.")
    return normalized


def _new_key() -> str:
    return Fernet.generate_key().decode("utf-8")


def _load_keyring() -> KeyringBackend:
    try:
        return import_module("keyring")
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
        raise LocalSecretVaultError("keyring is not installed.") from exc
