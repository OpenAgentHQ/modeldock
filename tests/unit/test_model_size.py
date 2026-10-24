"""Tests for the ModelSize value object. See issue #98."""

import pytest

from modeldock.domain.model import ModelSize


def test_format_params_billions():
    size = ModelSize(params=8_000_000_000, size_bytes=4_700_000_000)
    assert size.format_params() == "8B"


def test_format_params_with_decimal():
    size = ModelSize(params=1_500_000_000, size_bytes=1_000_000_000)
    assert size.format_params() == "1.5B"


def test_format_params_millions():
    size = ModelSize(params=350_000_000, size_bytes=200_000_000)
    assert size.format_params() == "350M"


def test_format_size_gb():
    size = ModelSize(params=8_000_000_000, size_bytes=4_700_000_000)
    assert size.format_size() == "4.7GB"


def test_str_combines_both():
    size = ModelSize(params=8_000_000_000, size_bytes=4_700_000_000)
    assert str(size) == "8B (4.7GB)"


def test_immutable():
    from pydantic import ValidationError

    size = ModelSize(params=8_000_000_000, size_bytes=4_700_000_000)
    with pytest.raises(ValidationError):
        size.params = 1  # type: ignore[misc]
