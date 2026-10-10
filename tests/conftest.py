from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT = PROJECT_ROOT / "configs" / "pilot.yaml"


@pytest.fixture
def pilot_path() -> Path:
    return PILOT


@pytest.fixture
def cfg(tmp_path):
    from failure_complementarity.config import load_experiment

    import os
    env = dict(os.environ, FC_RUNS_ROOT=str(tmp_path / "runs"))
    return load_experiment(PILOT, env=env)


@pytest.fixture(autouse=True)
def _cleanup_locked_dirs(tmp_path):
    """Tests create mode-000 dirs; make tmp_path removable afterwards."""
    yield
    import subprocess
    subprocess.run(["chmod", "-R", "u+rwX", str(tmp_path)], capture_output=True)
