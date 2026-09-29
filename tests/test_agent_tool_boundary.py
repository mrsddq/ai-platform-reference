"""The optional LLM path must use only passages returned by retrieval."""

import httpx
import pytest

from platform_app.api import _ollama_answer
from platform_app.config import Settings

HIT = {
    "point_id": "allowed-id",
    "citation": "[release@v1#chunk-1]",
    "sha256": "a" * 64,
    "text": "The synthetic release needs a canary gate.",
}


def run_agent(monkeypatch, replies):
    requests = []
    responses = iter(replies)

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"message": next(responses)})

    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(respond))
    )
    settings = Settings(api_key="unused", ollama_url="http://ollama:11434")
    return _ollama_answer("What is required?", [HIT], settings), requests


def test_agent_reads_allowlisted_source_and_cites_it(monkeypatch):
    answer, requests = run_agent(
        monkeypatch,
        [
            {
                "role": "assistant",
                "tool_calls": [
                    {"function": {"name": "get_source", "arguments": {"point_id": "allowed-id"}}}
                ],
            },
            {"role": "assistant", "content": "A canary gate is required [release@v1#chunk-1]."},
        ],
    )
    assert answer == "A canary gate is required [release@v1#chunk-1]."
    assert len(requests) == 2
    assert b"The synthetic release needs a canary gate" in requests[1].content


@pytest.mark.parametrize(
    "replies",
    [
        [{"role": "assistant", "content": "Trust me [release@v1#chunk-1]."}],
        [
            {
                "role": "assistant",
                "tool_calls": [
                    {"function": {"name": "get_source", "arguments": {"point_id": "outside-id"}}}
                ],
            }
        ],
        [
            {
                "role": "assistant",
                "tool_calls": [
                    {"function": {"name": "get_source", "arguments": {"point_id": "allowed-id"}}}
                ],
            },
            {"role": "assistant", "content": "False source [other@v1#chunk-9]."},
        ],
    ],
)
def test_agent_rejects_ungrounded_output(monkeypatch, replies):
    with pytest.raises(ValueError):
        run_agent(monkeypatch, replies)
