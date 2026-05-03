from typer.testing import CliRunner

from trading_system.app.cli import app


runner = CliRunner()


def test_secret_cli_set_list_delete_and_rotate(tmp_path, monkeypatch) -> None:
    keyring = _FakeKeyring()
    monkeypatch.setattr(
        "trading_system.infrastructure.local_secret_vault._load_keyring",
        lambda: keyring,
    )

    with runner.isolated_filesystem(temp_dir=tmp_path):
        set_result = runner.invoke(
            app,
            ["set-secret", "massive_api_key", "--value", "test-secret"],
            input="test-secret\n",
        )
        list_result = runner.invoke(app, ["list-secrets"])
        rotate_result = runner.invoke(app, ["rotate-master-key"])
        delete_result = runner.invoke(app, ["delete-secret", "MASSIVE_API_KEY"])
        empty_result = runner.invoke(app, ["list-secrets"])

    assert set_result.exit_code == 0
    assert "secret_name: MASSIVE_API_KEY" in set_result.output
    assert "test-secret" not in set_result.output
    assert list_result.exit_code == 0
    assert "secret_name: MASSIVE_API_KEY" in list_result.output
    assert "test-secret" not in list_result.output
    assert rotate_result.exit_code == 0
    assert "master_key_rotated: true" in rotate_result.output
    assert "secret_count: 1" in rotate_result.output
    assert delete_result.exit_code == 0
    assert "deleted_secret_name: MASSIVE_API_KEY" in delete_result.output
    assert empty_result.exit_code == 0
    assert "No local secrets found." in empty_result.output


class _FakeKeyring:
    def __init__(self) -> None:
        self.password = None

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.password

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.password = password
