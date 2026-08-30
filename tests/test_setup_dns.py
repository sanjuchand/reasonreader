from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "setup_dns.sh"


def test_dns_script_is_grey_cloud():
    text = SCRIPT.read_text()
    assert "proxied:false" in text
    assert "reasonreader.com" in text
    assert "144.126.135.134" in text
    assert "www." in text
