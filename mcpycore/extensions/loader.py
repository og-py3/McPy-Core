"""
ExtensionLoader — plugin/extension system for McPy-Core.

Extensions are Python modules that define a ``setup(client)`` coroutine.
They can register event handlers, inject middleware, and expose new APIs.

Usage::

    # my_extension.py
    async def setup(client):
        @client.on("chat")
        async def on_chat(message, sender):
            print(f"Extension heard: {message}")

    # In your bot:
    client.load_extension("my_extension")
    # or with a path:
    client.load_extension("bots.chat_logger")
"""
from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcpycore.client.client import MinecraftClient

log = logging.getLogger(__name__)


class ExtensionError(Exception):
    """Raised when an extension fails to load or unload."""


class Extension:
    """Represents one loaded extension."""

    __slots__ = ("name", "module", "setup_result")

    def __init__(self, name: str, module: Any, setup_result: Any = None) -> None:
        self.name = name
        self.module = module
        self.setup_result = setup_result

    def __repr__(self) -> str:
        return f"Extension({self.name!r})"


class ExtensionLoader:
    """
    Manages dynamic loading and unloading of extensions.

    Each extension module must expose either:
    - ``async def setup(client)`` — async initializer
    - ``def setup(client)`` — sync initializer

    Optionally:
    - ``async def teardown(client)`` — cleanup on unload
    """

    def __init__(self, client: "MinecraftClient") -> None:
        self._client = client
        self._loaded: dict[str, Extension] = {}

    def load(self, name: str, path: str | Path | None = None) -> Extension:
        """
        Load an extension by module name or file path.

        Parameters
        ----------
        name:
            Dotted module path (e.g. ``"bots.chat_logger"``) or a bare name.
        path:
            Optional filesystem path to load the module from.
        """
        if name in self._loaded:
            raise ExtensionError(f"Extension {name!r} is already loaded")

        try:
            if path is not None:
                spec = importlib.util.spec_from_file_location(name, path)
                if spec is None or spec.loader is None:
                    raise ExtensionError(f"Cannot load extension from path: {path}")
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)  # type: ignore[attr-defined]
            else:
                module = importlib.import_module(name)
        except ImportError as exc:
            raise ExtensionError(f"Cannot import extension {name!r}: {exc}") from exc

        if not hasattr(module, "setup"):
            raise ExtensionError(f"Extension {name!r} has no setup() function")

        setup = module.setup
        if asyncio.iscoroutinefunction(setup):
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(setup(self._client))
            except RuntimeError:
                # Already in an async context — schedule as task
                result = asyncio.ensure_future(setup(self._client))
        else:
            result = setup(self._client)

        ext = Extension(name=name, module=module, setup_result=result)
        self._loaded[name] = ext
        log.info("Loaded extension %r", name)
        return ext

    def unload(self, name: str) -> None:
        """Unload an extension by name."""
        if name not in self._loaded:
            raise ExtensionError(f"Extension {name!r} is not loaded")

        ext = self._loaded[name]

        teardown = getattr(ext.module, "teardown", None)
        if teardown is not None:
            if asyncio.iscoroutinefunction(teardown):
                try:
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(teardown(self._client))
                except RuntimeError:
                    asyncio.ensure_future(teardown(self._client))
            else:
                teardown(self._client)

        sys.modules.pop(name, None)
        del self._loaded[name]
        log.info("Unloaded extension %r", name)

    def reload(self, name: str) -> Extension:
        """Unload and reload an extension."""
        if name in self._loaded:
            path = getattr(self._loaded[name].module, "__file__", None)
            self.unload(name)
            return self.load(name, path=path)
        return self.load(name)

    @property
    def loaded(self) -> list[str]:
        """Names of all currently loaded extensions."""
        return list(self._loaded.keys())

    def is_loaded(self, name: str) -> bool:
        return name in self._loaded

    def __len__(self) -> int:
        return len(self._loaded)

    def __repr__(self) -> str:
        return f"ExtensionLoader([{', '.join(self._loaded)}])"
