"""
Last-directory state store for Supervertaler.

ConfigManager used to own the whole user_data pointer system (a
``.supervertaler_config.json`` in the user's home folder, first-launch folder
setup, api-keys migration). Since P1-B the data root is resolved solely by
``modules/portable_paths.py`` and none of that remains — this module survives
only for one piece of service state: the directory last used in a file dialog
(read/written by ``modules/file_dialog_helper.py``).

State file: ``<state_root()>\\last_directory.json`` (``state_root()`` is the
build root), format ``{"last_directory": "<path>"}``. It is NOT migrated from
the old home-directory file and the old file is never read or deleted.

Author: Michael Beijer
License: MIT
"""

import json
import logging
import os

from modules.portable_paths import state_root

logger = logging.getLogger(__name__)


class ConfigManager:
    """Remember the directory last used in a file dialog.

    The state is read from disk on every ``get_last_directory()`` call and
    written on every successful ``set_last_directory()`` call — no in-memory
    cache, so a fresh instance (or a fresh service after a data-path change)
    always sees the persisted value.
    """

    LAST_DIRECTORY_FILENAME = "last_directory.json"

    def __init__(self):
        """Initialize ConfigManager."""
        self.state_path = state_root() / self.LAST_DIRECTORY_FILENAME

    def _load_state(self) -> dict:
        """Load the state file. Return {} if missing or unreadable."""
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError) as e:
            if not isinstance(e, FileNotFoundError):
                logger.warning("[Config] Could not read %s: %s",
                               self.state_path, e)
            return {}

    def _write_state(self, state: dict) -> None:
        """Persist the state file. Quiet log on failure — a forgotten
        last-directory must never break a file dialog."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.warning("[Config] Could not write %s: %s",
                           self.state_path, e)

    def get_last_directory(self) -> str:
        """
        Get the last directory used in file dialogs.
        Returns empty string if no directory has been saved yet.
        """
        value = self._load_state().get('last_directory', '')
        return value if isinstance(value, str) else ''

    def set_last_directory(self, directory: str) -> None:
        """
        Save the last directory used in file dialogs.

        Args:
            directory: Full path to the directory to remember
        """
        if directory and os.path.isdir(directory):
            self._write_state(
                {'last_directory': os.path.normpath(directory)})

    def update_last_directory_from_file(self, file_path: str) -> None:
        """
        Extract and save the directory from a file path.

        Args:
            file_path: Full path to a file
        """
        if file_path:
            self.set_last_directory(os.path.dirname(file_path))


# Convenience function for easy access
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get or create the global ConfigManager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
