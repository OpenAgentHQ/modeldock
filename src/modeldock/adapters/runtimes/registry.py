"""RuntimeRegistry - discovers and maps runtimes to factories.

Supports entry-point discovery (third-party plugins) and built-in adapters.
See Architecture.md S4/S14.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, cast

from modeldock.common.logging import get_logger
from modeldock.domain.model import RuntimeBackend
from modeldock.ports.runtime import RuntimePort

# Built-in registry: first-party adapters shipped in-repo.
_BUILTIN: Dict[RuntimeBackend, Callable[[], RuntimePort]] = {}


def _register_builtins() -> None:
    from modeldock.adapters.runtimes.gpt4all import Gpt4AllRuntime
    from modeldock.adapters.runtimes.jan import JanRuntime
    from modeldock.adapters.runtimes.llamacpp import LlamaCppRuntime
    from modeldock.adapters.runtimes.lmstudio import LMStudioRuntime
    from modeldock.adapters.runtimes.ollama import OllamaRuntime
    from modeldock.adapters.runtimes.vllm import VllmRuntime

    _BUILTIN[RuntimeBackend.OLLAMA] = lambda: OllamaRuntime()
    _BUILTIN[RuntimeBackend.LM_STUDIO] = lambda: LMStudioRuntime()
    _BUILTIN[RuntimeBackend.LLAMACPP] = lambda: LlamaCppRuntime()
    _BUILTIN[RuntimeBackend.JAN] = lambda: JanRuntime()
    _BUILTIN[RuntimeBackend.GPT4ALL] = lambda: Gpt4AllRuntime()
    _BUILTIN[RuntimeBackend.VLLM] = lambda: VllmRuntime()


class RuntimeRegistry:
    """Resolves a RuntimeBackend to a runtime instance."""

    def __init__(self) -> None:
        self._logger = get_logger("runtime.registry")
        _register_builtins()
        self._entry_points: Dict[RuntimeBackend, Callable[[], RuntimePort]] = {}
        self._discover_entry_points()

    def _discover_entry_points(self) -> None:
        try:
            from importlib.metadata import entry_points

            eps = entry_points()
            if hasattr(eps, "select"):
                group: Any = eps.select(group="modeldock.runtimes")
            else:
                group = list(eps.get("modeldock.runtimes", []))
            for ep in group:
                try:
                    backend = RuntimeBackend.from_value(ep.name)
                    runtime_cls = ep.load()
                    loaded = cast(RuntimePort, runtime_cls())
                    self._entry_points[backend] = self._make_factory(loaded)
                except Exception as exc:  # skip bad plugins
                    self._logger.warning("Skipping runtime plugin %s: %s", ep.name, exc)
        except Exception as exc:
            self._logger.debug("Entry-point discovery unavailable: %s", exc)

    def get(self, backend: RuntimeBackend, host: str | None = None) -> RuntimePort:
        """Return a runtime instance for backend (entry points win).

        ``host`` is forwarded to the Ollama adapter so a configured host
        override always applies (the client is built lazily per instance).
        """
        factory = self._entry_points.get(backend) or _BUILTIN.get(backend)
        if factory is None:
            raise KeyError(f"No runtime registered for backend {backend.value!r}")
        runtime = factory()
        if host is not None and backend == RuntimeBackend.OLLAMA:
            try:
                runtime._host = host  # type: ignore[attr-defined]
            except Exception:  # nosec B110 - built-in adapter supports _host
                pass
        return runtime

    @staticmethod
    def _make_factory(instance: RuntimePort) -> Callable[[], RuntimePort]:
        """Wrap an already-built instance in a no-arg factory."""
        return lambda: instance

    def available_backends(self) -> List[RuntimeBackend]:
        """Return all known backends (built-in + discovered)."""
        known = set(_BUILTIN) | set(self._entry_points)
        return list(known)

    def detect_available(self) -> List[RuntimeBackend]:
        """Return backends whose runtime is currently installed/reachable."""
        result: List[RuntimeBackend] = []
        for backend in self.available_backends():
            try:
                runtime = self.get(backend)
                if runtime.is_available():
                    result.append(backend)
            except Exception:  # nosec B112 - skip backends that fail to probe
                continue
        return result


__all__ = ["RuntimeRegistry"]
