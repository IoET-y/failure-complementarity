"""The published CSV must reproduce the numbers quoted in the write-up (guards against silent edits)."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "results" / "data" / "branches.csv"


@pytest.fixture(scope="module")
def numbers(tmp_path_factory):
    if not CSV.exists():
        pytest.skip("results/data/branches.csv not present")
    spec = importlib.util.spec_from_file_location("analyze_from_csv", ROOT / "scripts" / "analyze_from_csv.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = tmp_path_factory.mktemp("n") / "n.json"
    import sys
    argv, sys.argv = sys.argv, ["x", "--csv", str(CSV), "--json", str(out)]
    try:
        mod.main()
    finally:
        sys.argv = argv
    return json.loads(out.read_text())


def test_screening_solve_counts(numbers):
    s = numbers["screening"]
    assert {m: v["solved"] for m, v in s.items()} == {
        "qwen": 9, "devstral": 24, "qwen36moe": 31, "qwen36dense": 32, "glm47flash": 18, "gptoss120b": 3, "nemotron3nano": 4}
    assert all(v["n"] == 40 for v in s.values())


def test_pilot_v2_primaries_and_pair_table(numbers):
    assert numbers["pilot_v2_primary"]["devstral"]["all"] == [17, 60]
    assert numbers["pilot_v2_primary"]["glm47flash"]["all"] == [16, 60]
    assert numbers["pilot_v2_failures"] == {"devstral": 43, "glm47flash": 44}
    assert numbers["pilot_v2_pair_2x2"] == {"both": 10, "only_devstral": 7, "only_glm": 6, "neither": 37}


def test_pooled_recovery_counts(numbers):
    t = numbers["pilot_v2_pooled"]["all"]
    assert t["devstral"]["table"]["V0 devstral->devstral"]["k"] == 18
    assert t["glm47flash"]["table"]["V0 glm47flash->glm47flash"]["per_replicate"] == [[1, 44], [9, 44], [3, 44]]
    assert t["glm47flash"]["table"]["note glm47flash->glm47flash"]["per_replicate"] == [[8, 44], [4, 44], [4, 44]]


def test_combined_contrasts(numbers):
    c = numbers["contrasts"]["all"]
    assert c["COMBINED FTV"]["mean"] == pytest.approx(-0.059, abs=5e-4)
    assert c["COMBINED FTV"]["ci95"] == pytest.approx([-0.130, 0.006], abs=1.5e-3)
    assert c["COMBINED CTV"]["mean"] == pytest.approx(0.0, abs=5e-4)
    assert c["COMBINED HRG_V0"]["mean"] == pytest.approx(0.015, abs=5e-4)
