import logging


def setup_logger(name=__name__, level=logging.DEBUG):
    from core.settings_store import SettingsStore
    from core.settings_base import BaseSettings

    try:
        settings = SettingsStore.get()
    except ValueError:
        settings = BaseSettings()  # fallback for test discovery or early imports

    logger = logging.getLogger(str(settings.LOG_FILE))
    if not logger.handlers:
        handler = logging.FileHandler(settings.LOG_FILE)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger

