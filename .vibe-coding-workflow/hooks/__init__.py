#!/usr/bin/env python3
import argparse
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional


class HookResult:
    def __init__(self, name: str, success: bool, blocking: List[str] = None, 
                 warnings: List[str] = None, suggestions: List[str] = None,
                 metadata: Dict[str, Any] = None):
        self.name = name
        self.success = success
        self.blocking = blocking if blocking is not None else []
        self.warnings = warnings if warnings is not None else []
        self.suggestions = suggestions if suggestions is not None else []
        self.metadata = metadata if metadata is not None else {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "success": self.success,
            "blocking": self.blocking,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "metadata": self.metadata
        }

    def has_blocking(self) -> bool:
        return len(self.blocking) > 0


class BaseHook(ABC):
    name: str = "base_hook"
    description: str = "Base hook"
    enabled: bool = True
    timeout: int = 300
    
    def __init__(self, config: Dict[str, Any] = {}):
        self.config = config
        self._parser = None
    
    @abstractmethod
    def run(self, context: Dict[str, Any]) -> HookResult:
        pass
    
    def setup_parser(self, parser: argparse.ArgumentParser):
        pass
    
    def parse_args(self, args: List[str]) -> Dict[str, Any]:
        if self._parser is None:
            self._parser = argparse.ArgumentParser(add_help=False)
            self.setup_parser(self._parser)
        return vars(self._parser.parse_args(args))
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "name": cls.name,
            "description": cls.description,
            "enabled": {"type": "boolean", "default": cls.enabled},
            "timeout": {"type": "integer", "default": cls.timeout}
        }


class HookRegistry:
    _hooks: Dict[str, type] = {}
    
    @classmethod
    def register(cls, hook_class: type):
        if issubclass(hook_class, BaseHook):
            cls._hooks[hook_class.name] = hook_class
        return hook_class
    
    @classmethod
    def get(cls, name: str) -> Optional[type]:
        return cls._hooks.get(name)
    
    @classmethod
    def list_hooks(cls) -> Dict[str, type]:
        return cls._hooks.copy()
    
    @classmethod
    def create_instance(cls, name: str, config: Dict[str, Any] = {}) -> Optional[BaseHook]:
        hook_class = cls.get(name)
        if hook_class:
            return hook_class(config)
        return None


def hook(enabled: bool = True, timeout: int = 300):
    def decorator(cls):
        cls.enabled = enabled
        cls.timeout = timeout
        return HookRegistry.register(cls)
    return decorator
