"""Appointment service specification tests."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.models.enums import AppointmentStatus, JobStatus
from app.services.appointment_service import AppointmentService


class BulkCancelAppointmentsSpec(unittest.TestCase):
    def _appointment(self, appt_id: str, status: AppointmentStatus = AppointmentStatus.SCHEDULED):
        appt = MagicMock()
        appt.id = appt_id
        appt.status = status
        return appt

    def test_bulk_cancel_cancels_active_and_skips_missing_or_cancelled(self) -> None:
        db = MagicMock()
        active_a = self._appointment("a1")
        active_b = self._appointment("a2")
        already = self._appointment("a3", AppointmentStatus.CANCELLED)

        query = MagicMock()
        query.filter.return_value = query
        query.all.return_value = [active_a, active_b, already]
        db.query.return_value = query

        job_query = MagicMock()
        job_query.filter.return_value = job_query
        linked_job = MagicMock()
        linked_job.status = JobStatus.SCHEDULED
        job_query.first.side_effect = [linked_job, None, None]

        with patch.object(db, "query", side_effect=[query, job_query, job_query, job_query]):
            result = AppointmentService.bulk_cancel_appointments(
                db,
                "biz-1",
                ["a1", "a2", "a3", "missing", "a1"],
            )

        self.assertEqual(result, {"cancelled": 2, "skipped": 2})
        self.assertEqual(active_a.status, AppointmentStatus.CANCELLED)
        self.assertEqual(active_b.status, AppointmentStatus.CANCELLED)
        self.assertEqual(linked_job.status, JobStatus.CANCELLED)
        db.commit.assert_called_once()

    def test_bulk_cancel_empty_list(self) -> None:
        db = MagicMock()
        result = AppointmentService.bulk_cancel_appointments(db, "biz-1", [])
        self.assertEqual(result, {"cancelled": 0, "skipped": 0})
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
