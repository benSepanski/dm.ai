"""Tests for AI-backend readiness checks and provider-error categorization."""

from __future__ import annotations

from unittest.mock import patch

import anthropic
import pytest

from dm_api.ai.backends import check_ai_readiness
from dm_api.ai.backends.anthropic_backend import _to_backend_error
from dm_api.ai.backends.base import AIErrorCategory


def test_readiness_anthropic_real_key_is_ready():
    result = check_ai_readiness("anthropic", "sk-ant-abc123")
    assert result.ready is True
    assert result.provider == "anthropic"


@pytest.mark.parametrize("key", ["", "test-key", "your-api-key", "placeholder"])
def test_readiness_anthropic_placeholder_not_ready(key):
    result = check_ai_readiness("anthropic", key)
    assert result.ready is False
    assert "ANTHROPIC_API_KEY" in result.detail


def test_readiness_claude_cli_requires_binary():
    with patch("dm_api.ai.backends.factory.shutil.which", return_value=None):
        result = check_ai_readiness("claude_cli")
    assert result.ready is False
    assert "claude" in result.detail.lower()

    with patch("dm_api.ai.backends.factory.shutil.which", return_value="/usr/local/bin/claude"):
        result = check_ai_readiness("claude_cli")
    assert result.ready is True


def test_readiness_unknown_provider_not_ready():
    assert check_ai_readiness("bogus").ready is False


def _api_error(cls: type) -> anthropic.APIError:
    """Build an anthropic error instance without hitting the network."""
    return cls.__new__(cls)


def test_error_mapping_auth():
    err = _to_backend_error(_api_error(anthropic.AuthenticationError))
    assert err.category is AIErrorCategory.AUTH
    assert "ANTHROPIC_API_KEY" in err.message


def test_error_mapping_rate_limit():
    err = _to_backend_error(_api_error(anthropic.RateLimitError))
    assert err.category is AIErrorCategory.RATE_LIMIT


def test_error_mapping_other_is_transient():
    err = _to_backend_error(_api_error(anthropic.APIConnectionError))
    assert err.category is AIErrorCategory.TRANSIENT
