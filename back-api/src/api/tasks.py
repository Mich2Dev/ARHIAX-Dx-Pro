"""
Task launcher — delegates to pipeline_runner.
The worker process (worker.py) picks up pending diagnostics from PostgreSQL.
This module is kept for API compatibility only.
"""

from __future__ import annotations

import logging

log = logging.getLogger("arhiax.tasks")


def run_pipeline(diagnostic_id: str, request_id: str, payload: dict) -> None:
    """
    Called by the API after creating a diagnostic record.
    The worker process will pick it up from the 'pending' queue in PostgreSQL.
    No threading, no Celery — the worker polls independently.
    """
    log.info("Diagnostic %s queued — worker will pick it up", diagnostic_id)


def continue_pipeline_from_g10a(diagnostic_id: str, survey_session_id: str) -> None:
    """
    Trigger pipeline continuation from G10a after survey is closed.
    The worker will detect the status change and continue execution.
    """
    log.info("Pipeline continuation queued for diagnostic %s with survey %s", 
             diagnostic_id, survey_session_id)
    # The worker.py will detect diagnostic.status == "running" and continue


def continue_pipeline_after_survey(diagnostic_id: str) -> None:
    """
    Trigger pipeline continuation after survey is closed.
    The worker will detect the status change and continue from G10a.
    """
    log.info("Pipeline continuation after survey for diagnostic %s", diagnostic_id)
    # The worker.py will detect diagnostic.status == "running" and continue from G10a

