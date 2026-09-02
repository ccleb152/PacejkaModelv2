"""Data-root configuration.

Every I/O-touching module in this package (raw TTC loading, segmented-file
read/write, fitted-parameter storage) reads the data root from here instead
of embedding a path -- see CLAUDE.md "Hard constraints" on why: the MATLAB
originals hardcode a Windows OneDrive path and a `"CC's tire model
folder\\Fitted Parameters\\"` relative path, neither of which survives a
new machine, OS, or team member.

Resolution order:
1. The `PACEJKA_DATA_ROOT` environment variable, if set.
2. A `data_root` key in a local TOML config file (default
   `~/.pacejka/config.toml`), written once via `set_data_root` -- this is
   what the Streamlit "configure data folder" page calls on first run.
3. Neither is set -> `DataRootNotConfigured`, with a message pointing at
   both ways to fix it.

Nothing here is committed to the repo; `.pacejka/` is in .gitignore.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".pacejka" / "config.toml"
_ENV_VAR = "PACEJKA_DATA_ROOT"


class DataRootNotConfigured(RuntimeError):
    """Raised when no data root is configured by env var or config file."""

    def __init__(self, config_path: Path):
        super().__init__(
            "No tire-data folder is configured. Fix this one of two ways:\n"
            f"  1. Set the {_ENV_VAR} environment variable to your locally "
            "synced OneDrive/SharePoint tire-data folder, or\n"
            f"  2. Call pacejka.config.set_data_root(<path>) once (the "
            f"Streamlit app's setup page does this for you), which writes "
            f"it to {config_path}."
        )


def _read_config_file(config_path: Path) -> str | None:
    if not config_path.is_file():
        return None
    with config_path.open("rb") as f:
        data = tomllib.load(f)
    return data.get("data_root")


def get_data_root(
    config_path: Path = DEFAULT_CONFIG_PATH, *, require_exists: bool = True
) -> Path:
    """Resolve the configured tire-data root directory.

    Raises DataRootNotConfigured if neither the environment variable nor
    the config file has a value set, and FileNotFoundError if a value is
    set but doesn't point at a real directory (require_exists=True, the
    default -- set False only for tests that don't need a real folder).
    """
    raw = os.environ.get(_ENV_VAR) or _read_config_file(config_path)
    if raw is None:
        raise DataRootNotConfigured(config_path)

    root = Path(raw).expanduser()
    if require_exists and not root.is_dir():
        raise FileNotFoundError(
            f"Configured tire-data root {root} does not exist or isn't a "
            "directory. Check the path (and that the OneDrive/SharePoint "
            "folder is actually synced locally)."
        )
    return root


def set_data_root(path: str | Path, config_path: Path = DEFAULT_CONFIG_PATH) -> Path:
    """Persist `path` as the tire-data root in the local TOML config file.

    Called once per machine/user -- by the Streamlit setup page in normal
    use, or directly for scripting/testing. Returns the resolved path.
    """
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"{root} does not exist or isn't a directory.")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    escaped = str(root).replace("\\", "\\\\").replace('"', '\\"')
    config_path.write_text(f'data_root = "{escaped}"\n')
    return root
