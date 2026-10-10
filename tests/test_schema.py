import pytest

from failure_complementarity.logging.schema import (
    EvalStatus as E,
    ExitReason as X,
    OutcomeClass as O,
    classify,
    is_primary_failure,
)


@pytest.mark.parametrize(
    "exit_reason,eval_status,outcome,status",
    [
        (X.SUBMITTED, E.SOLVED, O.SUCCESS, "SOLVED"),
        (X.PRIMARY_TIMEOUT, E.SOLVED, O.SUCCESS, "SOLVED"),  # partial diff graded, still solved
        (X.SUBMITTED, E.UNSOLVED, O.TASK_FAILURE, "UNSOLVED"),
        (X.PRIMARY_TIMEOUT, E.UNSOLVED, O.TASK_FAILURE, "PRIMARY_TIMEOUT"),
        (X.RECOVERY_TIMEOUT, E.UNSOLVED, O.TASK_FAILURE, "RECOVERY_TIMEOUT"),
        (X.FORMAT_ERROR_LIMIT, E.UNSOLVED, O.TASK_FAILURE, "UNSOLVED"),
        (X.CONTEXT_LIMIT, E.UNSOLVED, O.TASK_FAILURE, "UNSOLVED"),
        (X.MODEL_ERROR, E.UNSOLVED, O.INFRA_FAILURE, "MODEL_ERROR"),
        (X.MODEL_ERROR, E.SOLVED, O.INFRA_FAILURE, "MODEL_ERROR"),  # never counted either way
        (X.HARNESS_ERROR, E.NOT_EVALUATED, O.INFRA_FAILURE, "HARNESS_ERROR"),
        (X.CONTAINER_ERROR, E.UNSOLVED, O.INFRA_FAILURE, "CONTAINER_ERROR"),
        (X.SUBMITTED, E.EVALUATOR_ERROR, O.INFRA_FAILURE, "EVALUATOR_ERROR"),
        (X.SUBMITTED, E.NOT_EVALUATED, O.INFRA_FAILURE, "EVALUATOR_ERROR"),
    ],
)
def test_classify(exit_reason, eval_status, outcome, status):
    assert classify(exit_reason, eval_status) == (outcome, status)


def test_infra_failure_is_never_a_primary_failure():
    for d in ("budget_exhausted_and_unsolved", "unsolved_any_exit"):
        assert not is_primary_failure(X.MODEL_ERROR, E.UNSOLVED, d)
        assert not is_primary_failure(X.PRIMARY_TIMEOUT, E.EVALUATOR_ERROR, d)


def test_primary_failure_definitions():
    strict, loose = "budget_exhausted_and_unsolved", "unsolved_any_exit"
    assert is_primary_failure(X.PRIMARY_TIMEOUT, E.UNSOLVED, strict)
    assert not is_primary_failure(X.SUBMITTED, E.UNSOLVED, strict)
    assert is_primary_failure(X.SUBMITTED, E.UNSOLVED, loose)
    assert not is_primary_failure(X.PRIMARY_TIMEOUT, E.SOLVED, strict)
