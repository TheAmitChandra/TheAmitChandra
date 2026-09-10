"""Boundary checks for daily streaks and failure-safe activity updates."""

from datetime import date, datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from scripts import update_activity as activity


class ActivityTests(unittest.TestCase):
    def test_streak_continues_across_year_and_leap_day(self):
        days = {date(2024, 12, 31): 2, date(2025, 1, 1): 1}
        self.assertEqual(activity.streaks(days, date(2025, 1, 1)), (2, 2))
        days = {date(2024, 2, 28): 1, date(2024, 2, 29): 1, date(2024, 3, 1): 1}
        self.assertEqual(activity.streaks(days, date(2024, 3, 1)), (3, 3))

    def test_today_can_be_unfinished_but_yesterday_cannot(self):
        days = {date(2026, 9, 7): 1, date(2026, 9, 8): 2, date(2026, 9, 9): 0}
        self.assertEqual(activity.streaks(days, date(2026, 9, 9)), (2, 2))
        self.assertEqual(activity.streaks(days, date(2026, 9, 10)), (0, 2))

    def test_gaps_break_streaks_and_future_days_are_ignored(self):
        days = {date(2026, 9, 6): 1, date(2026, 9, 8): 1, date(2026, 9, 10): 1}
        self.assertEqual(activity.streaks(days, date(2026, 9, 9)), (1, 1))
        self.assertEqual(activity.streaks({}, date(2026, 9, 9)), (0, 0))

    def test_incomplete_api_calendar_is_rejected(self):
        responses = [
            {"user": {"createdAt": "2026-01-01T00:00:00Z", "contributionsCollection": {"contributionYears": [2026]}}},
            {"user": {"contributionsCollection": {"totalCommitContributions": 4, "contributionCalendar": {"weeks": []}}}},
        ]
        with patch.object(activity, "graphql", side_effect=responses):
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                activity.fetch_history(datetime(2026, 1, 2, tzinfo=timezone.utc))

    def test_failure_keeps_previous_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "card.svg"
            output.write_text("previous card", encoding="utf-8")
            with patch.object(activity, "OUTPUT", output), patch.object(activity, "fetch_history", side_effect=RuntimeError):
                with self.assertRaises(RuntimeError):
                    activity.main()
            self.assertEqual(output.read_text(encoding="utf-8"), "previous card")

    def test_svg_contains_accessible_exact_metrics(self):
        svg = activity.render(12345, 7, 101, 2024, date(2026, 9, 10))
        root = ElementTree.fromstring(svg)
        text = " ".join(root.itertext())
        self.assertIn("12,345 total commits, 7 day current streak, 101 day best streak", text)
        self.assertIn("2026-09-10 UTC", text)

    def test_contributions_are_not_mislabeled_as_commits(self):
        svg = activity.render(20819, 318, 318, 2024, date(2026, 9, 10), "contributions")
        text = " ".join(ElementTree.fromstring(svg).itertext())
        self.assertIn("TOTAL CONTRIBUTIONS", text)
        self.assertIn("20,819 total contributions", text)
        self.assertNotIn("TOTAL COMMITS", text)

    def test_each_metric_uses_its_own_api_field(self):
        responses = [
            {"user": {"createdAt": "2026-01-01T00:00:00Z", "contributionsCollection": {"contributionYears": [2026]}}},
            {"user": {"contributionsCollection": {
                "totalCommitContributions": 12,
                "restrictedContributionsCount": 90,
                "contributionCalendar": {"totalContributions": 105, "weeks": [
                    {"contributionDays": [{"date": "2026-01-01", "contributionCount": 105}]}
                ]},
            }}},
        ]
        for metric, expected in (("commits", 12), ("contributions", 105)):
            with self.subTest(metric=metric), patch.object(activity, "graphql", side_effect=responses):
                total, _, _ = activity.fetch_history(datetime(2026, 1, 1, 12, tzinfo=timezone.utc), metric)
                self.assertEqual(total, expected)

    def test_invalid_metric_is_rejected(self):
        with self.assertRaises(ValueError):
            activity.validate_metric("made-up")


if __name__ == "__main__":
    unittest.main()
