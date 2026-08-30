from pathlib import Path

PROD = Path(__file__).resolve().parents[1] / "docker-compose.prod.yml"


def test_prod_compose_binds_localhost_only():
    text = PROD.read_text()
    assert "127.0.0.1:3080:3000" in text
    assert "127.0.0.1:2024:2024" in text
    assert "127.0.0.1:5435:5432" in text
    assert "127.0.0.1:9100:9000" in text
    assert '"9000:9000"' not in text
    assert "0.0.0.0" not in text
