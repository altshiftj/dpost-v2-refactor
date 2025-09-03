from pathlib import Path

class GlobalSettings:
    """Application-wide configuration."""
    WATCH_DIR: Path = Path('.')
    DEST_DIR: Path = Path('.')
    RENAME_DIR: Path = Path('.')
    EXCEPTIONS_DIR: Path = Path('.')
    DEBOUNCE_TIME: float = 2.0
    LOG_FILE: Path = Path('app.log')
    KADI_SERVER: str = ''
    KADI_TOKEN: str = ''
