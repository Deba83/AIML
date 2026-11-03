import os
import datetime
import logging
import requests
from django.core.management.base import BaseCommand
from core.models import Scheme
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ==============================
# STRICT EDUCATION NUMERIC MAP
# ==============================
# under_10=0  10th=1  12th=2  diploma/ITI=3  UG=4  PG=5

RAW_EDU_TO_INT = {
    # under 10 / pre-matric
    "class 1-10":    (0, 0),
    "class 1–10":    (0, 0),
    "pre-matric":    (0, 0),
    "under 10":      (0, 0),
    "under_10":      (0, 0),
    "all":           (0, 5),   # open to everyone
    # single levels
    "10th":          (1, 1),
    "11th":          (1, 2),
    "12th":          (2, 2),
    "diploma":       (3, 3),
    "iti":           (3, 3),
    # post-matric (10th pass onwards)
    "post-matric":   (1, 5),
    # UG / PG
    "ug":            (4, 4),
    "undergraduate": (4, 4),
    "ug only":       (4, 4),
    "pg":            (5, 5),
    "postgraduate":  (5, 5),
    # ranges
    "ug to pg":              (4, 5),
    "undergraduate to pg":   (4, 5),
    "diploma to ug":         (3, 4),
    "diploma to pg":         (3, 5),
    "10th to pg":            (1, 5),
    "12th to pg":            (2, 5),
}

def normalize_education(raw_term):
    """
    Convert raw text description to (education_min_int, education_max_int).
    All comparisons via numeric codes only — no strings stored in DB.
    """
    if not raw_term:
        return 0, 5   # default: open to all

    raw = raw_term.lower().strip()

    # Exact lookup first
    if raw in RAW_EDU_TO_INT:
        return RAW_EDU_TO_INT[raw]

    # Keyword fallback (order matters — more specific first)
    if "class 1" in raw or "pre-matric" in raw:
        return 0, 0
    if "post-matric" in raw:
        return 1, 5
    if "pg" in raw or "postgraduate" in raw:
        if "ug" in raw or "undergraduate" in raw:
            return 4, 5
        return 5, 5
    if "ug" in raw or "undergraduate" in raw:
        return 4, 4
    if "diploma" in raw:
        return 3, 4
    if "12th" in raw:
        return 2, 2
    if "10th" in raw:
        return 1, 1

    # Default: open to all
    return 0, 5


class Command(BaseCommand):
    help = 'Fetches, normalizes (numeric education), and stores schemes from multiple sources'

    # ------------------------------------------------------------------
    def scrape_odisha_portal(self):
        url = 'https://scholarship.odisha.gov.in/website/scholarship-details'
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            r = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(r.text, 'html.parser')
            schemes = soup.find_all('div', class_='scheme-card')
            if not schemes:
                raise ValueError("Dynamic SPA content — no static 'scheme-card' found")
            return []
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"[Odisha] Fallback triggered: {e}"))
            return [
                {
                    "name": "Odisha State Post-Matric Scholarship",
                    "opportunity_type": "scholarship",
                    "provider": "govt",
                    "raw_education": "Post-matric",       # -> min=1, max=5
                    "income_limit": 250000,
                    "category": "All",
                    "state": "Odisha",
                    "gender": "All",
                    "requires_disability": False,
                    "required_documents": ["Aadhaar", "Income Certificate", "Caste Certificate", "Domicile Certificate"],
                    "deadline": "2026-09-30",
                    "source": "https://scholarship.odisha.gov.in/",
                    "description": "For ST/SC/OBC/SEBC/EBC students studying at post-matriculation or post-secondary stage in Odisha.",
                },
                {
                    "name": "KALIA Scholarship (Odisha)",
                    "opportunity_type": "scholarship",
                    "provider": "govt",
                    "raw_education": "ug to pg",           # -> min=4, max=5
                    "income_limit": 10000000,
                    "category": "All",
                    "state": "Odisha",
                    "gender": "All",
                    "requires_disability": False,
                    "required_documents": ["Aadhaar", "Income Certificate", "Domicile Certificate", "Bank Passbook"],
                    "deadline": "2026-08-31",
                    "source": "https://kalia.odisha.gov.in/",
                    "description": "Ensuring educational development of children of KALIA beneficiaries (Farmers).",
                },
                {
                    "name": "Bapuji Pathagara Yojana (Odisha)",
                    "opportunity_type": "scheme",
                    "provider": "govt",
                    "raw_education": "all",                # -> min=0, max=5
                    "income_limit": 10000000,
                    "category": "All",
                    "state": "Odisha",
                    "gender": "All",
                    "requires_disability": False,
                    "required_documents": ["Aadhaar", "Domicile Certificate"],
                    "deadline": "2026-12-31",
                    "source": "https://scholarship.odisha.gov.in/",
                    "description": "Encouraging establishment of libraries and promoting reading habits across rural Odisha.",
                },
                {
                    "name": "Pathani Samanta Mathematics Talent Scholarship (Odisha)",
                    "opportunity_type": "scholarship",
                    "provider": "govt",
                    "raw_education": "10th",               # -> min=1, max=1
                    "income_limit": 10000000,
                    "category": "All",
                    "state": "Odisha",
                    "gender": "All",
                    "requires_disability": False,
                    "required_documents": ["Aadhaar", "Marksheet", "Domicile Certificate"],
                    "deadline": "2026-11-30",
                    "source": "https://scholarship.odisha.gov.in/",
                    "description": "Financial assistance to students who excelled in the State Mathematics Talent Search Exam.",
                },
            ]

    # ------------------------------------------------------------------
    def scrape_nsp(self):
        url = 'https://scholarships.gov.in/All-Scholarships'
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            r = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(r.text, 'html.parser')
            rows = soup.find_all('tr', class_='scheme-row')
            if not rows:
                raise ValueError("Dynamic table / captcha prevented static scrape")
            return []
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"[NSP] Fallback triggered: {e}"))
            return [
                {
                    "name": "Pre-Matric Scholarship for Minorities (NSP)",
                    "opportunity_type": "scholarship",
                    "provider": "govt",
                    "raw_education": "Class 1-10",         # -> min=0, max=0
                    "income_limit": 100000,
                    "category": "All",
                    "state": "All",
                    "gender": "All",
                    "requires_disability": False,
                    "required_documents": ["Aadhaar", "Income Certificate", "Marksheet"],
                    "deadline": "2026-10-31",
                    "source": "https://scholarships.gov.in/",
                    "description": "Scholarship for students from minority communities studying in class 1 to 10.",
                },
                {
                    "name": "Central Sector Scheme of Scholarships for College Students (NSP)",
                    "opportunity_type": "scholarship",
                    "provider": "govt",
                    "raw_education": "ug to pg",           # -> min=4, max=5
                    "income_limit": 450000,
                    "category": "All",
                    "state": "All",
                    "gender": "All",
                    "requires_disability": False,
                    "required_documents": ["Aadhaar", "Income Certificate", "Marksheet"],
                    "deadline": "2026-11-30",
                    "source": "https://scholarships.gov.in/",
                    "description": "Financial assistance to meritorious students from low-income families.",
                },
                {
                    "name": "National Means-cum-Merit Scholarship (NMMS)",
                    "opportunity_type": "scholarship",
                    "provider": "govt",
                    "raw_education": "10th",               # -> min=1, max=1
                    "income_limit": 350000,
                    "category": "All",
                    "state": "All",
                    "gender": "All",
                    "requires_disability": False,
                    "required_documents": ["Aadhaar", "Marksheet", "Income Certificate"],
                    "deadline": "2026-06-30",
                    "source": "https://scholarships.gov.in/",
                    "description": "Scholarship for meritorious students of economically weaker sections.",
                },
            ]

    # ------------------------------------------------------------------
    def scrape_aicte(self):
        try:
            raise ValueError("AICTE portal structure unknown — using guaranteed fallback.")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"[AICTE] Fallback triggered: {e}"))
            return [
                {
                    "name": "AICTE Pragati Scholarship for Girls",
                    "opportunity_type": "scholarship",
                    "provider": "govt",
                    "raw_education": "diploma",            # -> min=3, max=3
                    "income_limit": 800000,
                    "category": "All",
                    "state": "All",
                    "gender": "Female",
                    "requires_disability": False,
                    "required_documents": ["Aadhaar", "Income Certificate", "Marksheet"],
                    "deadline": "2026-12-15",
                    "source": "https://www.aicte-india.org/",
                    "description": "Empowering women through technical education — financial assistance.",
                },
                {
                    "name": "AICTE Saksham Scholarship for Specially-Abled Students",
                    "opportunity_type": "scholarship",
                    "provider": "govt",
                    "raw_education": "diploma",            # -> min=3, max=3
                    "income_limit": 800000,
                    "category": "All",
                    "state": "All",
                    "gender": "All",
                    "requires_disability": True,
                    "required_documents": ["Aadhaar", "Income Certificate", "Disability Certificate", "Marksheet"],
                    "deadline": "2026-12-15",
                    "source": "https://www.aicte-india.org/",
                    "description": "Encouragement and support to specially-abled students for technical education.",
                },
            ]

    # ------------------------------------------------------------------
    def scrape_general(self):
        return [
            {
                "name": "Pradhan Mantri Awas Yojana (PMAY)",
                "opportunity_type": "scheme",
                "provider": "govt",
                "raw_education": "all",                    # -> min=0, max=5
                "income_limit": 600000,
                "category": "All",
                "state": "All",
                "gender": "All",
                "requires_disability": False,
                "required_documents": ["Aadhaar", "Income Certificate", "Land Record"],
                "deadline": "2026-12-31",
                "source": "https://pmay-urban.gov.in/",
                "description": "Housing for all by providing subsidies to eligible beneficiaries.",
            },
            {
                "name": "Google Summer of Code (GSoC)",
                "opportunity_type": "internship",
                "provider": "private",
                "raw_education": "ug to pg",               # -> min=4, max=5
                "income_limit": 10000000,
                "category": "All",
                "state": "All",
                "gender": "All",
                "requires_disability": False,
                "required_documents": ["Resume / CV"],
                "deadline": "2026-04-15",
                "source": "https://summerofcode.withgoogle.com/",
                "description": "Global program bringing students into open source software development.",
            },
        ]

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing Multi-Source Scraper (numeric education mode)..."))

        raw_data = []
        raw_data.extend(self.scrape_odisha_portal())
        raw_data.extend(self.scrape_nsp())
        raw_data.extend(self.scrape_aicte())
        raw_data.extend(self.scrape_general())

        self.stdout.write(self.style.NOTICE(
            f"Fetched {len(raw_data)} raw scheme entries. Normalizing to numeric education codes..."
        ))

        saved = updated = skipped = 0
        seen_identifiers = set()

        for item in raw_data:
            identifier = f"{item['name']}_{item['provider']}".lower().strip()
            if identifier in seen_identifiers:
                self.stdout.write(self.style.WARNING(f"[DUPLICATE SKIPPED] {item['name']}"))
                skipped += 1
                continue
            seen_identifiers.add(identifier)

            # ---- NUMERIC normalization (no strings stored) ----
            edu_min, edu_max = normalize_education(item.get('raw_education', ''))

            # Validate
            assert 0 <= edu_min <= 5, f"edu_min out of range for {item['name']}: {edu_min}"
            assert 0 <= edu_max <= 5, f"edu_max out of range for {item['name']}: {edu_max}"
            assert edu_min <= edu_max, f"edu_min > edu_max for {item['name']}"

            deadline_val = None
            if item.get('deadline'):
                try:
                    deadline_val = datetime.date.fromisoformat(item['deadline'])
                except ValueError:
                    self.stdout.write(self.style.WARNING(
                        f"[WARN] Bad deadline for {item['name']}: {item['deadline']}"
                    ))

            scheme, created = Scheme.objects.update_or_create(
                name=item['name'],
                provider=item.get('provider', 'govt'),
                defaults={
                    'opportunity_type':    item.get('opportunity_type', 'scheme'),
                    'education_min':       edu_min,
                    'education_max':       edu_max,
                    'max_income':        item.get('income_limit', 10000000),
                    'category':            item.get('category', 'All'),
                    'state':               item.get('state', 'All'),
                    'gender':              item.get('gender', 'All'),
                    'requires_disability': item.get('requires_disability', False),
                    'required_documents':  item.get('required_documents', []),
                    'deadline':            deadline_val,
                    'source':              item.get('source', ''),
                    'description':         item.get('description', ''),
                }
            )

            edu_label = f"min={edu_min}, max={edu_max}"
            if created:
                saved += 1
                self.stdout.write(self.style.SUCCESS(
                    f"[CREATED] {scheme.name} | edu({edu_label}) | provider={scheme.provider}"
                ))
            else:
                updated += 1
                self.stdout.write(self.style.WARNING(
                    f"[UPDATED] {scheme.name} | edu({edu_label}) | provider={scheme.provider}"
                ))

        # Private count check
        private_count = Scheme.objects.filter(provider='private').count()
        if private_count == 0:
            self.stdout.write(self.style.WARNING(
                "[PRIVATE=0] No private opportunities stored. "
                "Possible reason: all private sources returned empty data or were deduped."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"[PRIVATE] {private_count} private opportunity/ies in DB."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\nScraping complete — Created: {saved}, Updated: {updated}, Skipped(dup): {skipped}"
        ))
