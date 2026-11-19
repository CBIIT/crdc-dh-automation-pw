"""Guards BasePage helpers that do not need a browser.

Flow:
  1. _trim turns None and blank into None
  2. _trim strips surrounding whitespace
  3. _trim leaves a non-blank string
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from crdc_pw.pages.base import BasePage, _is_graphql_op


pytestmark = pytest.mark.unit


def test_trim_none_stays_none() -> None:
    """Filter kwargs that were never passed must stay None, not empty string."""
    assert BasePage._trim(None) is None


def test_trim_blank_becomes_none() -> None:
    """Whitespace-only filter values are skipped the same as missing ones."""
    assert BasePage._trim("") is None
    assert BasePage._trim("   ") is None


def test_trim_strips_and_keeps_text() -> None:
    """A real filter value is stripped, not dropped."""
    assert BasePage._trim("  autoQA  ") == "autoQA"


def _graphql_response(operation: str, variables: dict, url: str = "https://hub/api/graphql") -> SimpleNamespace:
    body = json.dumps({"operationName": operation, "variables": variables})
    return SimpleNamespace(url=url, request=SimpleNamespace(post_data=body))


def test_is_graphql_op_matches_operation_and_variables() -> None:
    """The response is for that operation and its variables include the wanted ones."""
    response = _graphql_response("retrievePropsForNodeType", {"nodeType": "study", "studyId": "1"})
    assert _is_graphql_op(response, "retrievePropsForNodeType", {"nodeType": "study"})


def test_is_graphql_op_rejects_other_operation_variable_or_url() -> None:
    response = _graphql_response("retrievePropsForNodeType", {"nodeType": "study"})
    assert not _is_graphql_op(response, "listReleasedDataRecords", {})
    assert not _is_graphql_op(response, "retrievePropsForNodeType", {"nodeType": "program"})
    other_url = _graphql_response("retrievePropsForNodeType", {}, url="https://hub/api/authn/session-ttl")
    assert not _is_graphql_op(other_url, "retrievePropsForNodeType", {})


def test_is_graphql_op_ignores_non_json_body() -> None:
    response = SimpleNamespace(url="https://hub/api/graphql", request=SimpleNamespace(post_data=None))
    assert not _is_graphql_op(response, "getMyUser", {})
