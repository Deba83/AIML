"""
management/commands/gemini_seed.py
====================================
Seeds the DB with:
  - 12 hard-coded, correctly-mapped Odisha/NSP schemes (always run first)
  - 30 Gemini API-generated national schemes

Deduplication: uses `scheme_code` unique field — runs get_or_create so re-running
the command never creates duplicates.

Education mapping (strict):
    0 = Under 10th (pre-matric, classes 1-9)
    1 = 10th passed
    2 = 12th passed
    3 = Diploma/ITI
    4 = UG
    5 = PG

Usage:
    python manage.py gemini_seed
"""

import os
import re
import json
import logging
import hashlib
from django.core.management.base import BaseCommand
from core.models import Scheme
from dotenv import load_dotenv

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

load_dotenv()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Odisha & NSP hard-coded seed (authoritative, no API dependency)
# Education levels verified against real scheme criteria
# ─────────────────────────────────────────────────────────────────────────────
SEED_SCHEMES = [
    # ── Pre-Matric Odisha ───────────────────────────────────────────────────
    {
        "scheme_code":      "ODISHA-SC-PREMATRIC",
        "name":             "Pre-Matric Scholarship for SC Students (Odisha)",
        "description":      "For SC students in classes 1–10 in Odisha (pre-matric level).",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 0, "education_max": 0,   # Under 10th only
        "min_income": 0,    "max_income": 250000,
        "category": "sc",   "state": "odisha",
        "gender": "All",    "min_marks": None, "requires_disability": False,
        "required_documents": ["Aadhaar", "Caste Certificate", "Income Certificate"],
        "benefits": "INR 1,500 per annum",
        "deadline": "2026-10-31",
        "source": "https://scholarship.odisha.gov.in/",
    },
    {
        "scheme_code":      "ODISHA-ST-PREMATRIC",
        "name":             "Pre-Matric Scholarship for ST Students (Odisha)",
        "description":      "For tribal (ST) students in classes 1–10 in Odisha.",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 0, "education_max": 0,   # Under 10th only
        "min_income": 0,    "max_income": 250000,
        "category": "st",   "state": "odisha",
        "gender": "All",    "min_marks": None, "requires_disability": False,
        "required_documents": ["Aadhaar", "Caste Certificate", "Income Certificate"],
        "benefits": "INR 1,200 per annum",
        "deadline": "2026-10-31",
        "source": "https://scholarship.odisha.gov.in/",
    },
    # ── Post-Matric Odisha (10th passed and above) ──────────────────────────
    {
        "scheme_code":      "ODISHA-SC-POSTMATRIC",
        "name":             "Post-Matric Scholarship for SC Students (Odisha)",
        "description":      "Financial assistance for SC students pursuing post-matric education in Odisha.",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 1, "education_max": 5,   # 10th to PG
        "min_income": 0,    "max_income": 250000,
        "category": "sc",   "state": "odisha",
        "gender": "All",    "min_marks": None, "requires_disability": False,
        "required_documents": ["Aadhaar", "Caste Certificate", "Income Certificate", "Domicile Certificate"],
        "benefits": "Full tuition fee + maintenance allowance",
        "deadline": "2026-09-30",
        "source": "https://scholarship.odisha.gov.in/",
    },
    {
        "scheme_code":      "ODISHA-ST-POSTMATRIC",
        "name":             "Post-Matric Scholarship for ST Students (Odisha)",
        "description":      "For tribal ST students pursuing post-matric education in Odisha.",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 1, "education_max": 5,
        "min_income": 0,    "max_income": 250000,
        "category": "st",   "state": "odisha",
        "gender": "All",    "min_marks": None, "requires_disability": False,
        "required_documents": ["Aadhaar", "Caste Certificate", "Income Certificate", "Domicile Certificate"],
        "benefits": "Full tuition fee + maintenance allowance",
        "deadline": "2026-09-30",
        "source": "https://scholarship.odisha.gov.in/",
    },
    {
        "scheme_code":      "ODISHA-OBC-POSTMATRIC",
        "name":             "Post-Matric Scholarship for OBC/SEBC Students (Odisha)",
        "description":      "OBC/SEBC students pursuing post-matric courses in Odisha.",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 1, "education_max": 5,
        "min_income": 0,    "max_income": 150000,
        "category": "obc",  "state": "odisha",
        "gender": "All",    "min_marks": None, "requires_disability": False,
        "required_documents": ["Aadhaar", "Caste Certificate", "Income Certificate", "Domicile Certificate"],
        "benefits": "Tuition fee + maintenance allowance",
        "deadline": "2026-09-30",
        "source": "https://scholarship.odisha.gov.in/",
    },
    # ── NMMS (for 10th students in Odisha) ──────────────────────────────────
    {
        "scheme_code":      "NMMS-ODISHA",
        "name":             "NMMS Scholarship – Odisha (National Means-cum-Merit)",
        "description":      "For meritorious students from economically weaker sections studying in class 9–10 in Odisha.",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 0, "education_max": 1,   # Under 10th / 10th level
        "min_income": 0,    "max_income": 150000,
        "category": "all",  "state": "odisha",
        "gender": "All",    "min_marks": 55.0, "requires_disability": False,
        "required_documents": ["Aadhaar", "Income Certificate", "School Enrollment Certificate"],
        "benefits": "INR 12,000 per annum",
        "deadline": "2026-11-30",
        "source": "https://scholarships.gov.in/",
    },
    # ── Mukhyamantri Medhabruti (12th and above) ────────────────────────────
    {
        "scheme_code":      "ODISHA-MEDHABRUTI",
        "name":             "Mukhyamantri Medhabruti Scholarship (Odisha)",
        "description":      "Merit-cum-means scholarship for students who scored 60%+ in 10th board in Odisha.",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 2, "education_max": 5,   # 12th and above
        "min_income": 0,    "max_income": 600000,
        "category": "all",  "state": "odisha",
        "gender": "All",    "min_marks": 60.0, "requires_disability": False,
        "required_documents": ["Aadhaar", "10th Mark Sheet", "Income Certificate", "Domicile Certificate"],
        "benefits": "INR 5,000 to INR 15,000 per annum",
        "deadline": "2026-10-31",
        "source": "https://scholarship.odisha.gov.in/",
    },
    # ── Biju Kanya Ratna (women, 12th and above) ────────────────────────────
    {
        "scheme_code":      "ODISHA-BIJU-KANYA-RATNA",
        "name":             "Biju Kanya Ratna Scholarship (Odisha)",
        "description":      "For meritorious girl students from BPL families in Odisha pursuing 12th and above.",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 2, "education_max": 5,
        "min_income": 0,    "max_income": 100000,
        "category": "all",  "state": "odisha",
        "gender": "Female", "min_marks": 60.0, "requires_disability": False,
        "required_documents": ["Aadhaar", "Income Certificate", "BPL Certificate", "Domicile Certificate"],
        "benefits": "INR 10,000 per annum",
        "deadline": "2026-10-31",
        "source": "https://hte.odisha.gov.in/",
    },
    # ── KALIA (UG/PG Odisha, for farmer kids) ───────────────────────────────
    {
        "scheme_code":      "ODISHA-KALIA",
        "name":             "KALIA Scholarship for Farmer Children (Odisha)",
        "description":      "Educational assistance for children of KALIA beneficiary farmers in Odisha pursuing UG/PG.",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 4, "education_max": 5,   # UG to PG
        "min_income": 0,    "max_income": None,
        "category": "all",  "state": "odisha",
        "gender": "All",    "min_marks": None, "requires_disability": False,
        "required_documents": ["Aadhaar", "KALIA Card", "Domicile Certificate", "Bank Passbook"],
        "benefits": "Up to INR 50,000 per annum",
        "deadline": "2026-08-31",
        "source": "https://kalia.odisha.gov.in/",
    },
    # ── NSP Central schemes ──────────────────────────────────────────────────
    {
        "scheme_code":      "NSP-SC-POSTMATRIC-CENTRAL",
        "name":             "NSP Post-Matric Scholarship for SC Students (Central)",
        "description":      "National Scholarships Portal post-matric scholarship for SC students across India.",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 1, "education_max": 5,
        "min_income": 0,    "max_income": 250000,
        "category": "sc",   "state": "all",
        "gender": "All",    "min_marks": None, "requires_disability": False,
        "required_documents": ["Aadhaar", "Bank Passbook", "Income Certificate", "Caste Certificate"],
        "benefits": "INR 2,000 to INR 16,000 per annum",
        "deadline": "2026-11-30",
        "source": "https://scholarships.gov.in/",
    },
    {
        "scheme_code":      "NSP-OBC-POSTMATRIC-CENTRAL",
        "name":             "NSP Post-Matric Scholarship for OBC Students (Central)",
        "description":      "National Scholarships Portal post-matric scholarship for OBC students across India.",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 1, "education_max": 5,
        "min_income": 0,    "max_income": 300000,
        "category": "obc",  "state": "all",
        "gender": "All",    "min_marks": None, "requires_disability": False,
        "required_documents": ["Aadhaar", "Bank Passbook", "Income Certificate", "Caste Certificate"],
        "benefits": "INR 5,000 per annum",
        "deadline": "2026-11-30",
        "source": "https://scholarships.gov.in/",
    },
    {
        "scheme_code":      "NSP-MINORITY-PREMATRIC-CENTRAL",
        "name":             "NSP Pre-Matric Scholarship for Minorities (Central)",
        "description":      "For minority students studying in classes 1–10 across India.",
        "opportunity_type": "scholarship", "provider": "govt",
        "education_min": 0, "education_max": 0,
        "min_income": 0,    "max_income": 100000,
        "category": "all",  "state": "all",
        "gender": "All",    "min_marks": None, "requires_disability": False,
        "required_documents": ["Aadhaar", "Income Certificate", "Minority Community Certificate"],
        "benefits": "INR 1,000 per annum",
        "deadline": "2026-11-30",
        "source": "https://scholarships.gov.in/",
    },
]


def _make_code(name: str) -> str:
    """Generate a deterministic scheme_code from name."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip())[:50]
    return f"GEMINI-{slug}"


def _clean_income(val):
    """Return int or None."""
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _clean_date(val) -> str | None:
    """Return 'YYYY-MM-DD' string or None."""
    s = str(val or "").strip()
    return s if re.match(r"^\d{4}-\d{2}-\d{2}$", s) else None


def _save_scheme(data: dict, verbosity_fn=None) -> tuple[bool, bool, str]:
    """
    Save or update a scheme. Returns (success, created, error_msg).
    """
    code = data.get("scheme_code") or _make_code(data.get("name", "unnamed"))

    otype = (data.get("opportunity_type") or "scholarship").lower()
    if otype not in ("scholarship", "internship", "fellowship", "scheme"):
        otype = "scholarship"

    provider = (data.get("provider") or "govt").lower()
    if provider not in ("govt", "private", "ngo"):
        provider = "govt"

    cat = (data.get("category") or "all").lower()
    if cat not in ("general", "obc", "sc", "st", "all", "ews"):
        cat = "all"

    state_raw = str((data.get("state") or "all")).lower().strip()
    if state_raw in ("national", "all india", "pan india"):
        state_raw = "all"

    try:
        edu_min = int(data.get("education_min", 0) or 0)
        edu_max = int(data.get("education_max", 5) or 5)
        edu_min = max(0, min(5, edu_min))
        edu_max = max(0, min(5, edu_max))
        if edu_min > edu_max:
            edu_min, edu_max = edu_max, edu_min
    except (TypeError, ValueError):
        edu_min, edu_max = 0, 5

    defaults = dict(
        name=(data.get("name") or "Unnamed Scheme")[:250],
        description=data.get("description") or "",
        opportunity_type=otype,
        provider=provider,
        education_min=edu_min,
        education_max=edu_max,
        min_income=_clean_income(data.get("min_income")),
        max_income=_clean_income(data.get("max_income")),
        category=cat,
        state=state_raw,
        gender=data.get("gender") or "All",
        min_marks=data.get("min_marks") or None,
        requires_disability=bool(data.get("requires_disability", False)),
        required_documents=data.get("required_documents") or [],
        benefits=data.get("benefits") or "",
        deadline=_clean_date(data.get("deadline")),
        source=str(data.get("source") or "")[:500],
    )

    try:
        obj, created = Scheme.objects.update_or_create(
            scheme_code=code,
            defaults=defaults
        )
        return True, created, ""
    except Exception as e:
        return False, False, str(e)


class Command(BaseCommand):
    help = "Seeds DB with strict, deduplicated Indian scholarship/internship data."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(self.style.NOTICE("Phase 1 — Seeding hard-coded Odisha/NSP schemes"))
        self.stdout.write(self.style.NOTICE("=" * 60))

        p1_ok = p1_upd = p1_fail = 0
        for item in SEED_SCHEMES:
            ok, created, err = _save_scheme(item)
            name = item.get("name", "?")[:55]
            if ok:
                if created:
                    p1_ok += 1
                    self.stdout.write(f"  [CREATE] {name}")
                else:
                    p1_upd += 1
                    self.stdout.write(f"  [UPDATE] {name}")
            else:
                p1_fail += 1
                self.stdout.write(self.style.ERROR(f"  [FAIL  ] {name} -> {err}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Phase 1 done: {p1_ok} created, {p1_upd} updated, {p1_fail} failed."
            )
        )

        # ── Phase 2: Gemini API ───────────────────────────────────────────
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or not GENAI_AVAILABLE:
            self.stdout.write(
                self.style.WARNING("Gemini API unavailable — skipping Phase 2.")
            )
            self._print_summary()
            return

        self.stdout.write(self.style.NOTICE("\n" + "=" * 60))
        self.stdout.write(self.style.NOTICE("Phase 2 — Fetching from Gemini API"))
        self.stdout.write(self.style.NOTICE("=" * 60))

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )

        prompt = """
You are an expert on Indian government scholarships and internships.
Return a JSON ARRAY of exactly 30 UNIQUE, REAL, DISTINCT Indian opportunities covering:
- 10 national scholarships from NSP (for SC, ST, OBC, minorities, general - different categories)
- 5 state-specific scholarships (Bihar, Maharashtra, Karnataka, West Bengal, UP — one each)
- 5 AICTE schemes (Pragati=Female/Diploma-UG, Saksham=Disability, SWANATH, etc.)
- 5 UGC/fellowship schemes (different levels)
- 5 recognized Govt or Private internships (DRDO, ISRO, UPSC, TCS, Microsoft)

STRICT RULES:
- Every entry must have a unique name. No duplicates.
- For EACH item use EXACTLY these keys:
  name, description, opportunity_type (scholarship/internship/fellowship/scheme),
  provider (govt/private/ngo), education_min (int 0-5), education_max (int 0-5),
  min_income (int or null), max_income (int or null), category (general/obc/sc/st/all),
  state (Indian state OR "all"), gender (Male/Female/All), min_marks (float or null),
  requires_disability (boolean), required_documents (array), benefits (string),
  deadline (YYYY-MM-DD or null), source (URL string)

STRICT EDUCATION RULES:
  0=under 10th (pre-matric), 1=10th passed, 2=12th passed, 3=diploma/ITI, 4=UG, 5=PG
  EXAMPLES:
  - Pre-matric schemes: education_min=0, education_max=0
  - Post-matric schemes: education_min=1, education_max=5
  - UG only: education_min=4, education_max=4
  - Pragati (Diploma/UG): education_min=3, education_max=4
  - Saksham scholarships: requires_disability=true

INCOME RULES:
  - Use null when there is no income restriction (especially for internships/fellowships)
  - Use realistic INR values (e.g. 250000, 800000) when income criteria exist

Do NOT include any Odisha-specific schemes (those are seeded separately).
Return ONLY valid JSON array, no markdown fences.
"""

        self.stdout.write("Calling Gemini (this may take 20-40 seconds)...")
        try:
            response = model.generate_content(prompt)
            schemes_data = json.loads(response.text)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Gemini API error: {e}"))
            self._print_summary()
            return

        if not isinstance(schemes_data, list):
            self.stdout.write(self.style.ERROR("Gemini returned non-list. Aborting Phase 2."))
            self._print_summary()
            return

        self.stdout.write(
            self.style.SUCCESS(f"Gemini returned {len(schemes_data)} items.")
        )

        p2_ok = p2_upd = p2_fail = 0
        for item in schemes_data:
            ok, created, err = _save_scheme(item)
            name = (item.get("name") or "?")[:55]
            if ok:
                if created:
                    p2_ok += 1
                    self.stdout.write(f"  [CREATE] {name}")
                else:
                    p2_upd += 1
                    self.stdout.write(f"  [UPDATE] {name}")
            else:
                p2_fail += 1
                self.stdout.write(self.style.ERROR(f"  [FAIL  ] {name} -> {err}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Phase 2 done: {p2_ok} created, {p2_upd} updated, {p2_fail} failed."
            )
        )
        self._print_summary()

    def _print_summary(self):
        total = Scheme.objects.count()
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"TOTAL SCHEMES IN DB : {total}"))
        self.stdout.write("=" * 60)
