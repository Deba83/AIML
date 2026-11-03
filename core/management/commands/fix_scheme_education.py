"""
management/commands/fix_scheme_education.py
=============================================
Automatically corrects incorrect education_min / education_max values
in the Scheme table by detecting scheme type from the scheme name.

RULES:
    "pre-matric" or "pre matric"   -> education_min=0, education_max=0
    "post-matric" or "post matric" -> education_min=1, education_max=5
    "fellowship" or "jrf" or "srf" -> education_min=5, education_max=5    (PG+)
    "internship"                   -> education_min=3, education_max=5    (Diploma+)

    Name-based keyword detection (case-insensitive):
    Contains "ug" / "undergraduate"       -> education_min=4, education_max=4
    Contains "pg" / "postgraduate"        -> education_min=5, education_max=5
    Contains "diploma" / "iti"            -> education_min=3, education_max=3
    Contains "nmms" / "means-cum-merit"   -> education_min=0, education_max=1

    Schemes with ranges wider than needed (0-5) are flagged and corrected.
    Schemes already correctly ranged are skipped.

USAGE:
    python manage.py fix_scheme_education
    python manage.py fix_scheme_education --dry-run    (preview only, no DB changes)
"""

import re
from django.core.management.base import BaseCommand
from core.models import Scheme


# Detection rules: (regex_pattern, education_min, education_max, label)
# Order matters — first match wins.
RULES = [
    # Specific keywords first (narrow)
    (r"nmms|means[\s\-]*cum[\s\-]*merit",           0, 0, "NMMS / Means-cum-Merit (Below 10th only)"),
    (r"pre[\s\-_]*matric",                           0, 0, "Pre-Matric (Below 10th only)"),
    (r"post[\s\-_]*matric",                          1, 5, "Post-Matric (10th passed and above)"),
    (r"fellowship|jrf|srf|net\b",                    5, 5, "Fellowship / JRF / NET (PG only)"),
    (r"\binternship\b|\bapprenticeship\b|\byuvika\b",3, 5, "Internship (Diploma and above)"),
    (r"\bpg\b|post[\s\-]*graduat",                   5, 5, "PG level"),
    (r"\bug\b|under[\s\-]*graduat|degree",           4, 4, "UG level"),
    (r"\bdiploma\b|\biti\b",                         3, 3, "Diploma/ITI level"),
]


def _detect_range(name: str, opp_type: str = "") -> tuple[int, int, str] | None:
    """
    Detect the correct education range from scheme name and opportunity_type.
    Returns (edu_min, edu_max, label) or None if no rule matches.
    """
    text = f"{name} {opp_type}".lower().strip()
    for pattern, e_min, e_max, label in RULES:
        if re.search(pattern, text):
            return e_min, e_max, label
    return None


class Command(BaseCommand):
    help = "Fix incorrect education_min/education_max in Scheme records using name-based detection."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview corrections without saving to DB.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        mode = "DRY RUN" if dry_run else "LIVE"

        self.stdout.write(self.style.NOTICE(f"\n{'='*65}"))
        self.stdout.write(self.style.NOTICE(f" Fix Scheme Education Ranges  [{mode}]"))
        self.stdout.write(self.style.NOTICE(f"{'='*65}\n"))

        schemes = Scheme.objects.all().order_by("name")
        total = schemes.count()
        fixed = 0
        skipped = 0
        no_match = 0

        for scheme in schemes:
            name = scheme.name or ""
            opp_type = scheme.opportunity_type or ""
            old_min = scheme.education_min
            old_max = scheme.education_max

            result = _detect_range(name, opp_type)

            if result is None:
                no_match += 1
                self.stdout.write(f"  [SKIP] {name[:55]:<55}  (no rule matched, keeping {old_min}-{old_max})")
                continue

            new_min, new_max, label = result

            if old_min == new_min and old_max == new_max:
                skipped += 1
                self.stdout.write(f"  [ OK ] {name[:55]:<55}  ({old_min}-{old_max}) already correct")
                continue

            # Needs fixing
            fixed += 1
            self.stdout.write(self.style.WARNING(
                f"  [FIX ] {name[:55]:<55}  ({old_min}-{old_max}) -> ({new_min}-{new_max})  [{label}]"
            ))

            if not dry_run:
                scheme.education_min = new_min
                scheme.education_max = new_max
                scheme.save(update_fields=["education_min", "education_max"])

        # Summary
        self.stdout.write(f"\n{'='*65}")
        self.stdout.write(self.style.SUCCESS(
            f"  Total: {total}  |  Fixed: {fixed}  |  Already OK: {skipped}  |  No rule: {no_match}"
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "  [!] DRY RUN -- no changes saved. Run without --dry-run to apply."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("  [OK] All corrections saved to database."))
        self.stdout.write(f"{'='*65}\n")
