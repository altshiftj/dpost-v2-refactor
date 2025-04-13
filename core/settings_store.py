from typing import Optional

class SettingsStore:
    _settings: Optional[object] = None

    @classmethod
    def set(cls, settings: object) -> None:
        """
        Sets the global settings object. Should be called once at application startup.
        """
        cls._settings = settings

    @classmethod
    def get(cls) -> object:
        """
        Retrieves the global settings object.
        Raises an error if it hasn't been initialized.
        """
        if cls._settings is None:
            raise ValueError("Settings have not been initialized!")
        return cls._settings

    @classmethod
    def reset(cls) -> None:
        """
        Resets the settings (useful in tests or controlled environments).
        """
        cls._settings = None
