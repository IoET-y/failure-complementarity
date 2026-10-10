"""Statuses and record schemas shared by runner, evaluator and analysis.

Two orthogonal facts are recorded for every run, never collapsed into a generic "failed":
* ``ExitReason`` — why the agent phase ended;
* ``EvalStatus`` — what the official evaluator said about the final diff.
``classify`` derives the outcome class and the spec-level status from them.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ExitReason(str, Enum):
    SUBMITTED = "SUBMITTED"                    # agent issued the completion command
    PRIMARY_TIMEOUT = "PRIMARY_TIMEOUT"        # wall-clock budget reached (primary phase)
    RECOVERY_TIMEOUT = "RECOVERY_TIMEOUT"      # wall-clock budget reached (recovery phase)
    STEP_LIMIT = "STEP_LIMIT"                  # configured step cap reached
    FORMAT_ERROR_LIMIT = "FORMAT_ERROR_LIMIT"  # repeated malformed tool calls (model behaviour)
    CONTEXT_LIMIT = "CONTEXT_LIMIT"            # context window exhausted (model behaviour, same limit for all)
    MODEL_ERROR = "MODEL_ERROR"                # endpoint unreachable / server error after retries
    HARNESS_ERROR = "HARNESS_ERROR"            # bug or crash in the runner / mini-swe-agent
    CONTAINER_ERROR = "CONTAINER_ERROR"        # sandbox could not be created / died


class EvalStatus(str, Enum):
    SOLVED = "SOLVED"
    UNSOLVED = "UNSOLVED"
    EVALUATOR_ERROR = "EVALUATOR_ERROR"
    NOT_EVALUATED = "NOT_EVALUATED"


class OutcomeClass(str, Enum):
    SUCCESS = "SUCCESS"
    TASK_FAILURE = "TASK_FAILURE"
    INFRA_FAILURE = "INFRA_FAILURE"


class Phase(str, Enum):
    PRIMARY = "primary"
    RECOVERY = "recovery"   # conditions A (same model) and B (other model) on Repo_t^A
    CONTROL = "control"     # condition C: rescuer on Repo_0


INFRA_EXIT_REASONS = frozenset({ExitReason.MODEL_ERROR, ExitReason.HARNESS_ERROR, ExitReason.CONTAINER_ERROR})
BUDGET_EXIT_REASONS = frozenset({ExitReason.PRIMARY_TIMEOUT, ExitReason.RECOVERY_TIMEOUT, ExitReason.STEP_LIMIT})


def classify(exit_reason: ExitReason, eval_status: EvalStatus) -> tuple[OutcomeClass, str]:
    """Return (outcome class, spec status string).

    Infra problems invalidate the run even if the partial diff happens to pass: such a run did not
    happen under the protocol and must be retried, not counted (integrity rule 8).
    """
    if exit_reason in INFRA_EXIT_REASONS:
        return OutcomeClass.INFRA_FAILURE, exit_reason.value
    if eval_status in (EvalStatus.EVALUATOR_ERROR, EvalStatus.NOT_EVALUATED):
        return OutcomeClass.INFRA_FAILURE, EvalStatus.EVALUATOR_ERROR.value
    if eval_status is EvalStatus.SOLVED:
        return OutcomeClass.SUCCESS, "SOLVED"
    if exit_reason in (ExitReason.PRIMARY_TIMEOUT, ExitReason.RECOVERY_TIMEOUT):
        return OutcomeClass.TASK_FAILURE, exit_reason.value
    return OutcomeClass.TASK_FAILURE, "UNSOLVED"


def is_primary_failure(
    exit_reason: ExitReason,
    eval_status: EvalStatus,
    definition: Literal["budget_exhausted_and_unsolved", "unsolved_any_exit"],
) -> bool:
    """Protocol §4 (decision D-009 selects the definition)."""
    outcome, _ = classify(exit_reason, eval_status)
    if outcome is not OutcomeClass.TASK_FAILURE:
        return False
    if definition == "budget_exhausted_and_unsolved":
        return exit_reason in BUDGET_EXIT_REASONS
    return True


# --------------------------------------------------------------------------- trajectory events


class EventType(str, Enum):
    RUN_START = "run_start"
    MODEL_REQUEST = "model_request"
    MODEL_RESPONSE = "model_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FORMAT_ERROR = "format_error"
    CHECKPOINT = "checkpoint"
    EVALUATION = "evaluation"
    ERROR = "error"
    RUN_END = "run_end"


class TrajectoryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str          # ISO-8601 UTC
    run_id: str
    task_id: str
    agent: str
    seq: int                # monotonically increasing per run file
    step: int | None = None # agent step (model call index), if applicable
    event_type: EventType
    tool: str | None = None
    content: Any = None
    metadata: dict[str, Any] = {}
