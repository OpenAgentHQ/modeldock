"""Unit tests for Jan runtime capability normalization."""

from __future__ import annotations

import pytest

from modeldock.adapters.runtimes.jan import _map_jan_capabilities
from modeldock.domain.model import Capability


@pytest.mark.parametrize(
    ("jan_value", "expected"),
    [
        ("completion", Capability.COMPLETION),
        ("chat", Capability.CHAT),
        ("embeddings", Capability.EMBED),
        ("vision", Capability.VISION),
        ("reasoning", Capability.REASONING),
        ("tools", Capability.TOOL_USE),
    ],
)
def test_maps_known_jan_capabilities(jan_value: str, expected: Capability) -> None:
    assert _map_jan_capabilities([jan_value]) == [expected]


def test_normalizes_case_and_whitespace() -> None:
    assert _map_jan_capabilities(["  CHAT ", "VISION"]) == [
        Capability.CHAT,
        Capability.VISION,
    ]


def test_preserves_first_seen_order_and_deduplicates() -> None:
    assert _map_jan_capabilities(["tools", "chat", "TOOLS", "chat"]) == [
        Capability.TOOL_USE,
        Capability.CHAT,
    ]


@pytest.mark.parametrize("malformed", [None, "chat", {"capabilities": ["chat"]}, 42])
def test_ignores_missing_or_non_sequence_values(malformed: object) -> None:
    assert _map_jan_capabilities(malformed) == []


def test_ignores_unknown_and_non_string_values() -> None:
    assert _map_jan_capabilities(["unknown", None, 42, "chat"]) == [Capability.CHAT]
