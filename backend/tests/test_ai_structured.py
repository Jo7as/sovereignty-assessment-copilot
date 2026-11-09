"""Strukturierte Antworten der KI: Schema in der Anfrage, Prüfung der Antwort im Code."""

import json
from enum import StrEnum

import httpx2
import pytest
from pydantic import BaseModel, ConfigDict

from app.matching import ai


class Location(StrEnum):
    EU = "EU"
    NICHT_EU = "NICHT_EU"


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Location | None
    quote: str | None
    page: int | None


class Replies:
    """Ersetzt OpenRouter: liefert der Reihe nach die vorgegebenen Antworten."""

    def __init__(self, *contents):
        self.contents, self.bodies = list(contents), []

    def post(self, url, headers, json, timeout):
        self.bodies.append(json)
        content = self.contents.pop(0)
        if isinstance(content, Exception):
            raise content
        return Response(content)


class Response:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


def no_endpoints():
    request = httpx2.Request("POST", ai.OPENROUTER_URL)
    response = httpx2.Response(404, request=request, json={"error": {"message": "No endpoints"}})
    return httpx2.HTTPStatusError("404", request=request, response=response)


GOOD = json.dumps({"value": "EU", "quote": "Speicherung nur in der EU", "page": 3})


def test_schema_is_sent_and_only_providers_supporting_it_are_used(monkeypatch):
    replies = Replies(GOOD)
    monkeypatch.setattr(ai.httpx2, "post", replies.post)

    finding = ai.structured("geheim", "deepseek/deepseek-v4.1-flash", "Lies den Vertrag", Finding)

    body = replies.bodies[0]
    assert finding == Finding(value=Location.EU, quote="Speicherung nur in der EU", page=3)
    assert body["provider"] == {"data_collection": "deny", "require_parameters": True}
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == Finding.model_json_schema()


def test_invalid_answer_is_asked_again_once_with_the_error(monkeypatch):
    wrong = json.dumps({"value": "USA", "quote": "x", "page": 3})
    replies = Replies(wrong, GOOD)
    monkeypatch.setattr(ai.httpx2, "post", replies.post)

    finding = ai.structured("geheim", "m", "Lies den Vertrag", Finding)

    retry_prompt = replies.bodies[1]["messages"][0]["content"]
    assert finding.value == Location.EU
    assert retry_prompt.startswith("Lies den Vertrag")
    assert "value" in retry_prompt and "ungültig" in retry_prompt


def test_second_invalid_answer_raises(monkeypatch):
    replies = Replies("kein JSON", '{"value": "EU"}')
    monkeypatch.setattr(ai.httpx2, "post", replies.post)

    with pytest.raises(ai.InvalidAnswer):
        ai.structured("geheim", "m", "Lies den Vertrag", Finding)
    assert len(replies.bodies) == 2


def test_without_provider_for_schemas_the_answer_is_checked_in_code(monkeypatch):
    """Rückfall: Kein Anbieter ohne Datenspeicherung kann Schemas, also ohne Schema fragen."""
    replies = Replies(no_endpoints(), f"Hier die Antwort: {GOOD}")
    monkeypatch.setattr(ai.httpx2, "post", replies.post)

    finding = ai.structured("geheim", "m", "Lies den Vertrag", Finding)

    assert finding.page == 3
    assert "response_format" not in replies.bodies[1]
    assert replies.bodies[1]["provider"] == {"data_collection": "deny"}


def test_extra_fields_are_rejected():
    with pytest.raises(ai.InvalidAnswer):
        ai.parse_structured('{"value": "EU", "quote": null, "page": null, "extra": 1}', Finding)
