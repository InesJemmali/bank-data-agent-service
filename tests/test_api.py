"""
Tests for the api with FAKE LLM: no Ollama, no GPU, runs in seconds.
Everything else is real: fatsapi, requests, agent, tools, datasets, etc.

requrements: pip install pytest httpx
run: pytest -v tests/test_api.py
"""

import json
import os
import sys
from pathlib import Path
import pytest
import requests

ROOT = Path(__file__).resolve().parents[1] # the project folder, one level above tests/
os.chdir(ROOT)  # the code uses relative paths like data/
sys.path.insert(0,str(ROOT)) # so import api finds api.py

from fastapi.testclient import TestClient
import agent_conversation 
import api



def fake_chat(messages, tools=None, think=False):
    """ Pretend to be the LLM: ask for a tool, with a path it should not get.
    Second call: answer with a number read from the results. """
    if messages[-1]["role"] != "tool":
        return {"message": {"role": "assistant", "content": "", "tool_calls": [{
            "function": {"name": "group_aggregate", "arguments": {
                "path": "/etc/passwd", "group_by": "Merchant_Category",
                "value_column": "Amount", "how": "sum"}}}]}}
    travel = json.loads(messages[-1]["content"])["result"]["Travel"]
    return {"message": {"role": "assistant", "content": f"Travel total is {travel}."}}

@pytest.fixture
def client(monkeypatch):
    """Runs before each test, plug in the fake LLM, empty the sessions, give a test client."""
    monkeypatch.setattr(agent_conversation, "chat", fake_chat)
    api.sessions.clear()
    return TestClient(api.app)

def new_session(client, dataset="data/tx.csv"):
    """Start a new session on the given dataset, return the session_id."""
    r = client.post("/sessions", json={"dataset": dataset})
    assert r.status_code == 200
    return r.json()["session_id"]

def test_ask_returns_steps_and_answer(client):
    sid = new_session(client)
    r = client.post(f"/sessions/{sid}/ask", json={"question":"Total travel spending?"})
    assert r.status_code == 200    
    body = r.json()
    assert body["steps"][0]["tool"] == "group_aggregate"
    assert body["answer"].startswith("Travel total is ")

def test_model_cannot_choose_the_file(client):
    sid = new_session(client)
    body = client.post(f"/sessions/{sid}/ask", json={"question":"x"}).json()
    used = body["steps"][0]["arguments"]["path"]
    assert used.endswith("data/tx.csv")  # the model cannot choose a different file

def test_sessions_are_separate(client):
    a, b = new_session(client), new_session(client)
    client.post(f"/sessions/{a}/ask", json={"question":"x"})
    assert len(api.sessions[a].messages) > 3  # A has a question in its history
    assert len(api.sessions[b].messages) == 3  # B is untouched

def test_ollama_down_gives_503_and_rolls_back(client, monkeypatch):
    """If the LLM is down, the API should return 503 and not add a question to the session."""
    def ollama_down(*args, **kwargs):
        raise requests.ConnectionError("Connection refusedn")
    monkeypatch.setattr(agent_conversation, "chat", ollama_down)
    sid = new_session(client)
    r = client.post(f"/sessions/{sid}/ask", json={"question":"hello"})
    assert r.status_code == 503
    assert len(api.sessions[sid].messages) == 3  # no question added
    assert api.sessions[sid].lock.acquire(blocking=False)  # lock is released even after an error

def test_reset_and_delete(client):
    sid = new_session(client)
    client.post(f"/sessions/{sid}/ask", json={"question":"x"})
    r = client.post(f"/sessions/{sid}/reset")
    
    assert len(api.sessions[sid].messages) == 3
    assert client.delete(f"/sessions/{sid}").status_code == 200     
    assert client.post(f"/sessions/{sid}/ask", json={"question":"x"}).status_code == 404  # session gone