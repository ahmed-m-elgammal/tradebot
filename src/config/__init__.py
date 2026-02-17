"""
Configuration Module

Pydantic-based configuration management with environment-aware loading.
"""

from src.config.settings import Settings, load_config, get_config

__all__ = ['Settings', 'load_config', 'get_config']
