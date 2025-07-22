import json
import logging
import os
from functools import lru_cache
from typing import Dict, Any, Optional
from pathlib import Path

from config.config import Config


class LocalizationService:
    """
    A service for managing application localization with JSON files.

    Features:
    - Loads locale files from specified directory
    - Supports nested keys in JSON structure
    - Provides string formatting with variables
    - Caches loaded locales for performance
    - Automatic fallback to default language
    - File modification tracking for hot-reloading
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the localization service.

        Args:
            config: Application configuration containing locale settings
        """
        self._cached_locales: Dict[str, Dict[str, Any]] = {}
        self.config = config
        self.locales_dir = Path(config.LOCALES_DIRECTORY_PATH)
        self._fallback_lang = "ru"
        self._last_modified: Dict[str, float] = {}
        self.logger = logging.getLogger(__name__)

    @lru_cache(maxsize=10)
    def _load_locale(self, lang: str) -> Dict[str, Any]:
        """
        Load locale file from disk with caching and modification tracking.

        Args:
            lang: Language code to load (e.g., 'en', 'ru')

        Returns:
            Dictionary of localized strings for the requested language

        Raises:
            RuntimeError: If neither requested nor fallback language files exist
        """
        filepath = self.locales_dir / f"{lang}.json"

        # Check if file has been modified since last load
        current_mod_time = os.path.getmtime(filepath)
        if lang in self._last_modified and current_mod_time <= self._last_modified[lang]:
            return self._cached_locales[lang]

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._last_modified[lang] = current_mod_time
                self._cached_locales[lang] = data
                return data
        except FileNotFoundError:
            if lang != self._fallback_lang:
                # Attempt to load fallback language
                return self._load_locale(self._fallback_lang)
            raise RuntimeError(f"Locale files not found for language: {lang}")

    def get_text(self, key: str, lang: str = "ru", **kwargs) -> str:
        """
        Get localized text by key with optional variable substitution.

        Args:
            key: Dot-separated path to the text (e.g., 'menu.main.title')
            lang: Language code (defaults to 'ru')
            **kwargs: Variables to substitute in the text

        Returns:
            Localized string with substituted variables if provided,
            or fallback text if key not found

        Examples:
            >>> self.get_text("welcome.message", lang="en", username="John")
            "Welcome, John!"
        """
        try:
            texts = self._load_locale(lang)

            # Handle nested keys (e.g., "menu.main.title")
            if "." in key:
                key_parts = key.split(".")
                nested_text = self._get_nested_text(texts, key_parts)
                if nested_text is not None:
                    return self._format_text(nested_text, kwargs)

            # Handle flat keys
            if key in texts:
                return self._format_text(texts[key], kwargs)

        except Exception as e:
            self.logger.info(f"An error occurred with the LocalizationService: {e}")

        return f"[{key}]"  # Fallback for missing keys

    @staticmethod
    def _get_nested_text(texts: Dict[str, Any], key_parts: list[str]) -> Optional[str]:
        """
        Safely retrieve nested text from locale dictionary.

        Args:
            texts: Loaded locale dictionary
            key_parts: List of key parts (e.g., ['menu', 'main', 'title'])

        Returns:
            Found text as string or None if path doesn't exist
        """
        current = texts
        for part in key_parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return str(current) if isinstance(current, (str, int, float)) else None

    @staticmethod
    def _format_text(text: str, variables: Dict[str, Any]) -> str:
        """
        Format text with variables if any are provided.

        Args:
            text: The text to format
            variables: Dictionary of variables to substitute

        Returns:
            Formatted string if variables provided, original text otherwise
        """
        return text.format(**variables) if variables else text