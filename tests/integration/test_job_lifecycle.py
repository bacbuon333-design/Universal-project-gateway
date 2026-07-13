from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from universal_project_gateway.control_plane import ServiceError
from universal_project_gateway.service import GatewayService


def test_prepare_and_validate_replay_do_not_duplicate_job_effects(
    gateway_factory: Callable[[str], tuple[GatewayService, Path]],
) -> None:
    gateway, _ = gateway_factory("python_demo")

    first = gateway.prepare_task(
        "python-demo",
        "Change the greeting and run the tests",
        target_paths=["src/greeting.py"],
        requested_operation="edit",
        idempotency_key="prepare-greeting-001",
    )
    replay = gateway.prepare_task(
        "python-demo",
        "Change the greeting and run the tests",
        target_paths=["src/greeting.py"],
        requested_operation="edit",
        idempotency_key="prepare-greeting-001",
    )

    assert replay["idempotent_replay"] is True
    assert replay["job"]["job_id"] == first["job"]["job_id"]
    job_id = first["job"]["job_id"]
    gateway.replace_workspace_text(
        job_id,
        "src/greeting.py",
        'return "Hello"',
        'return "Hello from UPG"',
        max_replacements=1,
    )

    validated = gateway.validate(job_id, idempotency_key="validate-greeting-001")
    validated_replay = gateway.validate(job_id, idempotency_key="validate-greeting-001")

    assert validated_replay == validated
    assert validated["passed"] is True
    inspected = gateway.inspect_job(job_id)
    claim_events = [event for event in inspected["events"] if event["event_type"] == "job_claimed"]
    assert len(claim_events) == 2
    assert len(gateway.jobs.list(project_id="python-demo")) == 1


def test_cancelled_prepared_job_cannot_enter_validation(
    gateway_factory: Callable[[str], tuple[GatewayService, Path]],
) -> None:
    gateway, source = gateway_factory("python_demo")
    source_before = (source / "src" / "greeting.py").read_bytes()
    prepared = gateway.prepare_task(
        "python-demo",
        "Change the greeting and run the tests",
        target_paths=["src/greeting.py"],
        requested_operation="edit",
    )
    job_id = prepared["job"]["job_id"]

    cancelled = gateway.request_cancellation(job_id, reason="operator request")

    assert cancelled["job"]["status"] == "cancelled"
    assert cancelled["job"]["cancel_requested"] is True
    with pytest.raises(ServiceError) as blocked:
        gateway.validate(job_id, idempotency_key="cancelled-validation-001")
    assert blocked.value.code == "JOB_CANCELLED"
    with pytest.raises(ServiceError) as replayed_block:
        gateway.validate(job_id, idempotency_key="cancelled-validation-001")
    assert replayed_block.value.code == "JOB_CANCELLED"
    assert gateway.get_evidence(job_id)["verified"] is True
    assert (source / "src" / "greeting.py").read_bytes() == source_before
    event_types = {event["event_type"] for event in cancelled["events"]}
    assert {"cancellation_requested", "status_transition"} <= event_types
