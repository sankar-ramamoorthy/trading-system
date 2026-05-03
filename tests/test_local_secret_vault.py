import json

import pytest

from trading_system.infrastructure.local_secret_vault import (
    LocalSecretVault,
    LocalSecretVaultError,
    require_secret,
    resolve_secret,
)


def test_set_get_list_and_delete_secret_without_plaintext_file(tmp_path) -> None:
    vault = LocalSecretVault(tmp_path / "keys.enc", keyring_backend=_FakeKeyring())

    entry = vault.set_secret("massive_api_key", "test-secret")

    assert entry.name == "MASSIVE_API_KEY"
    assert vault.get_secret("MASSIVE_API_KEY") == "test-secret"
    assert [item.name for item in vault.list_secrets()] == ["MASSIVE_API_KEY"]
    assert b"test-secret" not in (tmp_path / "keys.enc").read_bytes()
    assert vault.delete_secret("MASSIVE_API_KEY") is True
    assert vault.get_secret("MASSIVE_API_KEY") is None
    assert vault.delete_secret("MASSIVE_API_KEY") is False


def test_resolve_secret_prefers_vault_over_environment(tmp_path) -> None:
    vault = LocalSecretVault(tmp_path / "keys.enc", keyring_backend=_FakeKeyring())
    vault.set_secret("MASSIVE_API_KEY", "vault-secret")

    assert (
        resolve_secret(
            "MASSIVE_API_KEY",
            vault=vault,
            environ={"MASSIVE_API_KEY": "env-secret"},
        )
        == "vault-secret"
    )


def test_resolve_secret_falls_back_to_environment_when_vault_has_no_secret(tmp_path) -> None:
    vault = LocalSecretVault(tmp_path / "keys.enc", keyring_backend=_FakeKeyring())

    assert (
        resolve_secret(
            "MASSIVE_API_KEY",
            vault=vault,
            environ={"MASSIVE_API_KEY": "env-secret"},
        )
        == "env-secret"
    )


def test_require_secret_raises_clear_missing_secret_error(tmp_path) -> None:
    vault = LocalSecretVault(tmp_path / "keys.enc", keyring_backend=_FakeKeyring())

    with pytest.raises(LocalSecretVaultError, match="MASSIVE_API_KEY is required"):
        require_secret("MASSIVE_API_KEY", vault=vault, environ={})


def test_rotate_master_key_preserves_stored_secrets(tmp_path) -> None:
    keyring = _FakeKeyring()
    vault = LocalSecretVault(tmp_path / "keys.enc", keyring_backend=keyring)
    vault.set_secret("MASSIVE_API_KEY", "test-secret")
    original_key = keyring.password

    count = vault.rotate_master_key()

    assert count == 1
    assert keyring.password != original_key
    assert vault.get_secret("MASSIVE_API_KEY") == "test-secret"


def test_invalid_vault_file_raises_clear_error(tmp_path) -> None:
    keyring = _FakeKeyring()
    vault = LocalSecretVault(tmp_path / "keys.enc", keyring_backend=keyring)
    vault.set_secret("MASSIVE_API_KEY", "test-secret")
    (tmp_path / "keys.enc").write_text(json.dumps({"bad": "data"}), encoding="utf-8")

    with pytest.raises(LocalSecretVaultError, match="could not be decrypted"):
        vault.list_secrets()


class _FakeKeyring:
    def __init__(self) -> None:
        self.password = None

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.password

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.password = password
