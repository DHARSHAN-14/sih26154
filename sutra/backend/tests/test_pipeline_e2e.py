from __future__ import annotations
import pytest
from app.orchestrator.stages import StageContext
from app.orchestrator.pipeline import run as run_pipeline
from app.core import events as event_bus


@pytest.mark.asyncio
async def test_pipeline_execution_all_stages():
    queue = event_bus.subscribe("test_session")

    ctx = StageContext(
        session_id="test_session",
        job_id="JOB-E2E-TEST",
        sot_id="SOT-TEST",
        artifact_dir="./data/artifacts",
        params={"model_backend": "fast", "language": "en"},
        source_paths=[],
        formats=["advisory", "executive_summary"],
    )

    await run_pipeline(ctx)

    captured_events = []
    while not queue.empty():
        evt = queue.get_nowait()
        captured_events.append((evt.stage, evt.status))

    event_bus.unsubscribe("test_session", queue)

    stages_run = [stg for stg, status in captured_events if status == "done"]

    # Pre-generation sequential stages
    for required in ["ingest", "sanitize", "route", "retrieve", "extract_facts", "build_kg", "build_sot", "lock_sot"]:
        assert required in stages_run, f"Stage {required} did not complete"

    # Per-format fanout stages
    for fmt in ["advisory", "executive_summary"]:
        assert f"plan:{fmt}" in stages_run
        assert f"generate:{fmt}" in stages_run
        assert f"validate_facts:{fmt}" in stages_run

    # Finalization
    assert "cross_check" in stages_run
    assert "finalize" in stages_run
