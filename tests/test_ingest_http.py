from ingest.http_server import authorized, parse_copy_id
import os

import pytest


def test_parse_copy_id_accepts_uuid():
    assert parse_copy_id(b'{"copyId":"6ffc4420-371b-41c6-a18c-146fe091ef11"}') == "6ffc4420-371b-41c6-a18c-146fe091ef11"


def test_parse_copy_id_rejects_junk():
    with pytest.raises(ValueError):
        parse_copy_id(b'{"copyId":"../etc/passwd"}')


def test_authorized_requires_bearer_token(monkeypatch):
    monkeypatch.setenv("INGEST_TOKEN", "secret")
    assert authorized("Bearer secret") is True
    assert authorized("Bearer other") is False
    assert authorized(None) is False
    monkeypatch.delenv("INGEST_TOKEN")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    assert authorized("Bearer secret") is False
