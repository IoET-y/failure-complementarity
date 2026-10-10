import math

from failure_complementarity.analysis.metrics import mcnemar_exact, paired, recovery_analysis, wilson


def R(outcome, **kw):
    return {"outcome_class": outcome, **kw}


S, F, I = "SUCCESS", "TASK_FAILURE", "INFRA_FAILURE"


def test_wilson_and_mcnemar():
    lo, hi = wilson(5, 10)
    assert 0.23 < lo < 0.24 and 0.76 < hi < 0.77
    assert all(math.isnan(v) for v in wilson(0, 0))
    assert mcnemar_exact(0, 0) == 1.0
    assert abs(mcnemar_exact(0, 6) - 2 * (1 / 64)) < 1e-12
    assert mcnemar_exact(3, 3) == 1.0


def test_paired_ignores_invalid():
    p = paired({"a": True, "b": False, "c": None, "d": True}, {"a": True, "b": True, "c": True, "d": False})
    assert (p.n, p.both, p.only_x, p.only_y, p.neither) == (3, 1, 1, 1, 0)


def test_recovery_analysis_hand_computed():
    # q fails primary on t1,t2,t3 (t4 solved, t5 failed by submission -> not a primary failure)
    res = {
        ("t1", "primary_q"): R(F, primary_failure=True), ("t2", "primary_q"): R(F, primary_failure=True),
        ("t3", "primary_q"): R(F, primary_failure=True), ("t4", "primary_q"): R(S, primary_failure=False),
        ("t5", "primary_q"): R(F, primary_failure=False),
        ("t1", "recovery_q_to_q"): R(F), ("t2", "recovery_q_to_q"): R(S), ("t3", "recovery_q_to_q"): R(F),
        ("t1", "recovery_q_to_d"): R(S), ("t2", "recovery_q_to_d"): R(S), ("t3", "recovery_q_to_d"): R(I),
        ("t1", "control_d_repo0"): R(F), ("t2", "control_d_repo0"): R(S), ("t3", "control_d_repo0"): R(S),
    }
    out = recovery_analysis(res, ["t1", "t2", "t3", "t4", "t5"], ["q", "d"])
    assert out["failed_q"] == ["t1", "t2", "t3"]
    qq, qd = out["pairs"]["q->q"], out["pairs"]["q->d"]
    assert (qq["R"]["k"], qq["R"]["n"]) == (1, 3)
    assert (qd["R"]["k"], qd["R"]["n"], qd["R"]["n_infra_or_missing"]) == (2, 2, 1)   # infra branch excluded
    assert qd["HRG"]["n"] == 2 and qd["HRG"]["diff"] == 0.5                      # t1: d✓ q✗ ; t2: both ✓
    assert (qd["control_repo0"]["k"], qd["control_repo0"]["n"]) == (2, 3)
    assert qd["FTV"]["n"] == 2 and qd["FTV"]["diff"] == 0.5                      # t1: rescue✓ ctrl✗ ; t2: both ✓
    assert "HRG" not in qq and out["failed_d"] == []
