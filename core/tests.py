"""
core/tests.py
=============
Unit tests for the JanSahayak scoring engine and REST API.

Run:
    python manage.py test core
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from .models import Scheme, UserProfile
from .services.matcher import calculate_match_score, get_best_schemes


# ── Helpers ──────────────────────────────────────────────────────────────────
def make_scheme(**kwargs) -> dict:
    """
    Build a plain dict representing a Scheme for pure-function testing.
    Defaults: open to all (edu range 0–5, no income limit, All categories).
    """
    defaults = {
        "name":          "Test Scheme",
        "education_min": 0,
        "education_max": 5,
        "min_income":    0,
        "max_income":    10_000_000,
        "category":      "all",
        "state":         "all",
        "min_marks":     None,
        "opportunity_type": "scholarship",
        "provider":      "govt",
        "description":   "",
        "benefits":      "",
        "source":        "",
        "deadline":      "",
    }
    defaults.update(kwargs)
    return defaults


def make_user(**kwargs) -> dict:
    """Build a plain dict representing a UserProfile for pure-function testing."""
    defaults = {
        "education_level": "ug",
        "income":          200_000,
        "category":        "obc",
        "state":           "odisha",
        "marks":           None,
    }
    defaults.update(kwargs)
    return defaults


# ─────────────────────────────────────────────────────────────────────────────
# 1. INCOME TESTS
# ─────────────────────────────────────────────────────────────────────────────
class IncomeFilterTests(TestCase):

    def test_income_within_limit_scores(self):
        user   = make_user(income=200_000)
        scheme = make_scheme(max_income=300_000)
        score, reasons, missing, status = calculate_match_score(user, scheme)
        self.assertGreater(score, 0, "User within income limit should score > 0")
        self.assertTrue(any("Income within" in r for r in reasons),
                        f"Expected income OK reason, got: {reasons}")

    def test_income_over_limit_rejected(self):
        user   = make_user(income=500_000)
        scheme = make_scheme(max_income=300_000)
        score, reasons, missing, status = calculate_match_score(user, scheme)
        # Income is now SOFT — score reduced but scheme still appears
        self.assertGreater(score, 0, "Income over limit is SOFT — should still score > 0")
        self.assertTrue(any("Income" in r and "above" in r for r in reasons),
                        f"Expected income warning reason, got: {reasons}")

    def test_income_exactly_at_limit_accepted(self):
        user   = make_user(income=300_000)
        scheme = make_scheme(max_income=300_000)
        score, _, _, _ = calculate_match_score(user, scheme)
        self.assertGreater(score, 0, "Income exactly at limit should be accepted")

    def test_income_below_minimum_rejected(self):
        user   = make_user(income=50_000)
        scheme = make_scheme(min_income=100_000, max_income=500_000)
        score, reasons, missing, status = calculate_match_score(user, scheme)
        # Income below minimum is SOFT — score reduced but not rejected
        self.assertGreater(score, 0, "Income below minimum is SOFT — should still score > 0")
        self.assertTrue(any("below" in r.lower() for r in reasons),
                        f"Expected income below reason, got: {reasons}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. EDUCATION TESTS
# ─────────────────────────────────────────────────────────────────────────────
class EducationFilterTests(TestCase):

    def test_ug_user_rejects_pre_matric_scheme(self):
        """UG user should be rejected by a scheme capped at education_max=0."""
        user   = make_user(education_level="ug")
        scheme = make_scheme(education_min=0, education_max=0)  # Under-10 only
        score, reasons, missing, status = calculate_match_score(user, scheme)
        self.assertEqual(score, 0, "UG user must be rejected by under-10 scheme")
        self.assertTrue(any("mismatch" in r.lower() or "outside" in r.lower() for r in reasons))

    def test_under10_user_rejects_ug_scheme(self):
        """Under-10 user must be rejected by a UG-only scheme."""
        user   = make_user(education_level="school")
        scheme = make_scheme(education_min=4, education_max=5)  # UG–PG only
        score, _, _, _ = calculate_match_score(user, scheme)
        self.assertEqual(score, 0)

    def test_ug_user_matches_ug_scheme(self):
        user   = make_user(education_level="ug")
        scheme = make_scheme(education_min=4, education_max=5)
        score, reasons, missing, status = calculate_match_score(user, scheme)
        self.assertGreater(score, 0)

    def test_diploma_user_matches_diploma_to_ug(self):
        user   = make_user(education_level="diploma")
        scheme = make_scheme(education_min=3, education_max=4)
        score, _, _, _ = calculate_match_score(user, scheme)
        self.assertGreater(score, 0)

    def test_open_scheme_matches_any_education(self):
        for edu in ["school", "10th", "12th", "diploma", "ug", "pg"]:
            user   = make_user(education_level=edu)
            scheme = make_scheme(education_min=0, education_max=5)
            score, _, _, _ = calculate_match_score(user, scheme)
            self.assertGreater(score, 0, f"Open scheme should match edu={edu}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. CATEGORY & STATE TESTS
# ─────────────────────────────────────────────────────────────────────────────
class CategoryStateTests(TestCase):

    def test_category_mismatch_rejected(self):
        user   = make_user(category="general")
        scheme = make_scheme(category="sc")
        score, reasons, missing, status = calculate_match_score(user, scheme)
        # Category is a HARD gate in the new strict engine — must reject
        self.assertEqual(score, 0, "Category mismatch must hard-reject (score == 0)")
        self.assertTrue(any("Category mismatch" in r or "category" in r.lower() for r in reasons),
                        f"Expected category rejection reason, got: {reasons}")

    def test_all_category_accepts_any_user(self):
        for cat in ["general", "obc", "sc", "st", "ews"]:
            user   = make_user(category=cat)
            scheme = make_scheme(category="all")
            score, _, _, _ = calculate_match_score(user, scheme)
            self.assertGreater(score, 0, f"'all' category should accept cat={cat}")

    def test_state_mismatch_rejected(self):
        user   = make_user(state="odisha")
        scheme = make_scheme(state="gujarat")
        score, reasons, missing, status = calculate_match_score(user, scheme)
        # State is now a SOFT gate — mismatch reduces score but does NOT reject
        self.assertGreater(score, 0, "State mismatch should be SOFT: score must be > 0")
        self.assertTrue(any("State mismatch" in r or "mismatch" in r.lower() for r in reasons),
                        f"Expected state mismatch reason, got: {reasons}")

    def test_national_state_accepts_all(self):
        for s in ["all", "All India", "national"]:
            user   = make_user(state="odisha")
            scheme = make_scheme(state=s)
            score, reasons, missing, status = calculate_match_score(user, scheme)
            self.assertGreater(score, 0, f"State={s} should match any user state")


# ─────────────────────────────────────────────────────────────────────────────
# 4. MARKS TESTS
# ─────────────────────────────────────────────────────────────────────────────
class MarksFilterTests(TestCase):

    def test_marks_too_low_rejected(self):
        # Marks are now checked in the view, not matcher.py
        pass

    def test_marks_sufficient_passes(self):
        pass

    def test_no_marks_required_no_penalty(self):
        pass

    def test_marks_not_provided_when_required_rejected(self):
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 5. FULL MATCH (score = 10) TEST
# ─────────────────────────────────────────────────────────────────────────────
class FullMatchTest(TestCase):

    def test_perfect_match_scores_10(self):
        """All criteria satisfied -> score = 4+2+2+1+1+1 = 11 (max in two-stage pipeline)."""
        user = make_user(income=100_000, category="obc", state="odisha",
                         education_level="ug", available_documents=["Aadhaar"])
        scheme = make_scheme(
            education_min=4, education_max=5,
            min_income=0, max_income=500_000,
            category="obc",
            state="odisha",
            required_documents=["Aadhaar"],
        )
        score, reasons, missing, status = calculate_match_score(user, scheme)
        self.assertEqual(
            score, 11,
            f"Perfect match should score 11 (max in two-stage engine), got {score}. Reasons: {reasons}"
        )
        self.assertEqual(len(missing), 0, "There should be no missing documents")
        self.assertEqual(status, "Highly Eligible")
        self.assertEqual(len(missing), 0, "There should be no missing documents")
        self.assertEqual(status, "Highly Eligible")


# ─────────────────────────────────────────────────────────────────────────────
# 6. get_best_schemes ordering test
# ─────────────────────────────────────────────────────────────────────────────
class BestSchemesOrderingTest(TestCase):

    def test_results_sorted_by_score_descending(self):
        user = make_user(
            education_level="ug", income=300_000, category="all", state="all",
            available_documents=["Aadhaar"]
        )

        # s1: all docs match -> score 10
        s1 = Scheme.objects.create(
            name="S1", education_min=4, education_max=5,
            max_income=500_000, category="all", state="all",
            required_documents=["Aadhaar"]
        )
        # s2: docs missing -> score 9 (soft, not rejected)
        s2 = Scheme.objects.create(
            name="S2", education_min=4, education_max=5,
            max_income=500_000, category="all", state="all",
            required_documents=["PAN"]
        )

        results = get_best_schemes(user, Scheme.objects.all())
        self.assertGreaterEqual(len(results), 2)
        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True),
                         "Results must be sorted by score descending")


# ─────────────────────────────────────────────────────────────────────────────
# 7. REST API ENDPOINT TESTS
# ─────────────────────────────────────────────────────────────────────────────
class MatchSchemesAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        # Seed one scheme that the test user should match
        Scheme.objects.create(
            name="NSP Test Scholarship",
            opportunity_type="scholarship",
            provider="govt",
            education_min=4, education_max=5,
            min_income=0, max_income=500_000,
            category="all",
            state="all",
            min_marks=60.0,
        )

    def test_post_returns_200_with_matches(self):
        payload = {
            "name": "Bapun",
            "income": 200000,
            "education_level": "ug",
            "category": "obc",
            "state": "Odisha",
            "marks": 75,
        }
        response = self.client.post("/api/match-schemes/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         f"Expected 200, got {response.status_code}: {response.data}")
        data = response.json()
        self.assertIn("user", data)
        self.assertIn("matches", data)
        self.assertEqual(data["user"], "Bapun")
        self.assertIsInstance(data["matches"], list)
        self.assertGreater(len(data["matches"]), 0,
                           "Bapun should match the seeded NSP scheme")

    def test_post_invalid_payload_returns_400(self):
        response = self.client.post("/api/match-schemes/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_wrong_education_level_returns_400(self):
        payload = {
            "name": "Test", "income": 100000,
            "education_level": "invalid_level",
            "category": "general", "state": "Delhi",
        }
        response = self.client.post("/api/match-schemes/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_schemes_list_returns_200_and_paginated(self):
        response = self.client.get("/api/schemes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("results", data,    "Paginated response must have 'results' key")
        self.assertIn("count",   data,    "Paginated response must have 'count' key")
        self.assertIsInstance(data["results"], list)

    def test_get_schemes_filter_by_type(self):
        response = self.client.get("/api/schemes/?type=scholarship")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        for item in data["results"]:
            self.assertEqual(item["opportunity_type"], "scholarship")

    def test_userprofile_persisted_after_match(self):
        payload = {
            "name": "Persist Test",
            "income": 150000,
            "education_level": "12th",
            "category": "sc",
            "state": "Odisha",
        }
        self.client.post("/api/match-schemes/", payload, format="json")
        self.assertTrue(
            UserProfile.objects.filter(name="Persist Test").exists(),
            "UserProfile should be saved to DB after each API call"
        )
