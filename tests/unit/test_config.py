"""Unit tests for pacejka.config. Not a MATLAB port -- no golden fixtures,
just ordinary behavioral tests."""

import pytest

from pacejka.config import DataRootNotConfigured, get_data_root, set_data_root


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    # Guard every test against a real PACEJKA_DATA_ROOT leaking in from the
    # actual shell environment.
    monkeypatch.delenv("PACEJKA_DATA_ROOT", raising=False)


def test_raises_when_nothing_configured(tmp_path):
    missing_config = tmp_path / "does_not_exist.toml"
    with pytest.raises(DataRootNotConfigured):
        get_data_root(config_path=missing_config)


def test_env_var_takes_precedence(tmp_path, monkeypatch):
    env_root = tmp_path / "from_env"
    env_root.mkdir()
    file_root = tmp_path / "from_file"
    file_root.mkdir()
    config_path = tmp_path / "config.toml"
    set_data_root(file_root, config_path=config_path)

    monkeypatch.setenv("PACEJKA_DATA_ROOT", str(env_root))

    assert get_data_root(config_path=config_path) == env_root


def test_set_data_root_then_get_data_root_round_trips(tmp_path):
    data_root = tmp_path / "tire_data"
    data_root.mkdir()
    config_path = tmp_path / "nested" / "config.toml"

    returned = set_data_root(data_root, config_path=config_path)
    assert returned == data_root.resolve()
    assert get_data_root(config_path=config_path) == data_root.resolve()


def test_set_data_root_rejects_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        set_data_root(tmp_path / "nope", config_path=tmp_path / "config.toml")


def test_get_data_root_rejects_missing_directory_when_require_exists(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('data_root = "/definitely/not/a/real/path"\n')
    with pytest.raises(FileNotFoundError):
        get_data_root(config_path=config_path)


def test_get_data_root_can_skip_existence_check(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('data_root = "/definitely/not/a/real/path"\n')
    result = get_data_root(config_path=config_path, require_exists=False)
    assert str(result) == "/definitely/not/a/real/path"


def test_set_data_root_escapes_backslashes_and_quotes(tmp_path):
    # Windows-style paths (backslashes) and any path containing a quote
    # must round-trip correctly through the hand-written TOML string.
    data_root = tmp_path / 'weird "quoted" dir'
    data_root.mkdir()
    config_path = tmp_path / "config.toml"

    set_data_root(data_root, config_path=config_path)
    assert get_data_root(config_path=config_path) == data_root.resolve()
