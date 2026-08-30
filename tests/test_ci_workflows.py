from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / ".github/workflows/ci.yml").read_text()
DEPLOY = (ROOT / ".github/workflows/deploy.yml").read_text()


def test_ci_runs_pytest_and_vitest():
    assert "uv run pytest" in CI
    assert "OPENAI_API_KEY: ci-not-a-real-key" in CI
    assert "pnpm test" in CI
    assert "pull_request" in CI
    assert "branches: [main]" in CI


def test_deploy_waits_for_green_ci_on_main():
    assert "workflow_run" in DEPLOY
    assert "workflows: [CI]" in DEPLOY
    assert "conclusion == 'success'" in DEPLOY
    assert "./scripts/deploy.sh" in DEPLOY
    assert "tailscale/github-action@v4" in DEPLOY
    assert "TS_OAUTH_CLIENT_ID" in DEPLOY
    assert "TS_OAUTH_SECRET" in DEPLOY
    assert "VPS_SSH_KEY" in DEPLOY
    assert "VPS_HOST" in DEPLOY
    assert "VPS_SSH_KNOWN_HOSTS" in DEPLOY
    assert "tag:ci" in DEPLOY
    assert "ping:" in DEPLOY

