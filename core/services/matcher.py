"""
services/matcher.py — Production Eligibility Engine (Two-Stage Pipeline)
=========================================================================
ARCHITECTURE:
    Stage 1 → HARD FILTER  (eliminate impossible matches)
    Stage 2 → SOFT SCORING (rank remaining by relevance)

EDUCATION HIERARCHY:
    0 = school / under_10   (currently studying below 10th)
    1 = 10th                (passed 10th)
    2 = 12th                (passed 12th)
    3 = diploma / iti
    4 = ug
    5 = pg

SCORING (max 10):
    Education   : 4 pts (always awarded — passed hard filter)
    Category    : 2 pts (always awarded — passed hard filter)
    Income      : 2 pts (soft — reduce, never reject)
    Documents   : 1 pt  (soft)
    Age         : 1 pt  (soft)

HARD FILTERS (instant disqualification):
    - Education out of [education_min, education_max]
    - Category mismatch (unless scheme.category == "all")
    - State mismatch (unless scheme.state is national/all)
    - Gender mismatch (unless scheme.gender == "All")
    - Disability required but user not disabled
    - Scheme expired
    - Internship shown to school/10th/12th user

RESULT QUALITY:
    - Remove score < 4 (too irrelevant)
    - Sort by score DESC
    - Fallback: if nothing passes, return top 5 closest (score > 0)
    - NEVER return empty list if any scheme exists
"""

from __future__ import annotations
import datetime
import logging
import re

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EDU_RANK = {
    "school": 0, "under_10": 0,
    "10th": 1,
    "12th": 2,
    "diploma": 3, "iti": 3,
    "ug": 4,
    "pg": 5,
}

EDU_LABEL = {
    0: "Below 10th", 1: "10th", 2: "12th",
    3: "Diploma/ITI", 4: "UG", 5: "PG",
}

NATIONAL_STATES = frozenset({"all", "all india", "national", "pan india", ""})

INTERNSHIP_MIN_LEVEL = 3  # diploma and above only


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _g(obj, key, default=None):
    """Get attribute from ORM model or dict."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _edu_int(level) -> int:
    """Convert education string to integer rank. Returns -1 if unrecognised."""
    return EDU_RANK.get(str(level or "").lower().strip(), -1)


def _safe_int(val, default=None):
    """Convert to int or return default."""
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _lower(val, fallback="") -> str:
    return str(val or fallback).lower().strip()


def _today() -> datetime.date:
    return datetime.date.today()


def _is_pre_matric(scheme) -> bool:
    """Detect if scheme is clearly Pre-Matric from its name."""
    name = _lower(_g(scheme, "name"))
    return bool(re.search(r"pre[\s\-_]*matric", name))


def _is_post_matric(scheme) -> bool:
    """Detect if scheme is clearly Post-Matric from its name."""
    name = _lower(_g(scheme, "name"))
    return bool(re.search(r"post[\s\-_]*matric", name))


def _sanitise_edu_range(scheme) -> tuple[int, int]:
    """
    Return (edu_min, edu_max) with data-sanity corrections.
    Fixes overly wide ranges like 0-5 when scheme name implies Pre/Post-Matric.
    """
    raw_min = _safe_int(_g(scheme, "education_min"), 0)
    raw_max = _safe_int(_g(scheme, "education_max"), 5)
    s_min = max(0, min(5, raw_min))
    s_max = max(0, min(5, raw_max))
    if s_min > s_max:
        s_min, s_max = s_max, s_min

    # Data sanity guard: fix wide ranges based on scheme name
    if _is_pre_matric(scheme):
        s_max = min(s_max, 0)  # Pre-matric is strictly BEFORE 10th pass (rank 0)
    elif _is_post_matric(scheme):
        s_min = max(s_min, 1)  # Post-matric starts at 10th pass (rank 1)

    return s_min, s_max


def _edu_label_for_user(user_edu_int: int) -> str:
    """Human-readable label for the user's education level."""
    return EDU_LABEL.get(user_edu_int, f"Level {user_edu_int}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STAGE 1: HARD FILTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _hard_filter(user, scheme) -> tuple[bool, str]:
    """
    Returns (passed: bool, rejection_reason: str).
    If passed is False, the scheme is completely ineligible.
    """
    user_edu = _edu_int(_g(user, "education_level"))

    # 1. EXPIRY CHECK
    deadline = _g(scheme, "deadline", None)
    if deadline:
        try:
            if isinstance(deadline, str):
                deadline = datetime.datetime.strptime(deadline, "%Y-%m-%d").date()
            if isinstance(deadline, datetime.date) and deadline < _today():
                return False, "Scheme has expired"
        except ValueError:
            pass

    # 2. EDUCATION RANGE
    s_min, s_max = _sanitise_edu_range(scheme)

    if user_edu == -1:
        return False, "Unrecognised education level"
    if not (s_min <= user_edu <= s_max):
        user_label = _edu_label_for_user(user_edu)
        range_label = f"{EDU_LABEL.get(s_min, '?')} - {EDU_LABEL.get(s_max, '?')}"
        return False, f"Education level ({user_label}) outside scheme range ({range_label})"

    # 3. INTERNSHIP CONTROL: only for diploma/UG/PG
    opp_type = _lower(_g(scheme, "opportunity_type"))
    if opp_type == "internship" and user_edu < INTERNSHIP_MIN_LEVEL:
        return False, "Internships require at least Diploma level"

    # 4. CATEGORY
    scheme_cat = _lower(_g(scheme, "category"), "all")
    user_cat = _lower(_g(user, "category"), "all")
    if scheme_cat not in ("all", "") and scheme_cat != user_cat:
        return False, (
            f"Category mismatch: scheme is for {scheme_cat.upper()} students, "
            f"you are {user_cat.upper()}"
        )

    # 5. GENDER
    scheme_gender = _lower(_g(scheme, "gender"), "all")
    user_gender = _lower(_g(user, "gender"))
    if scheme_gender not in ("all", "any", ""):
        if user_gender and user_gender != scheme_gender:
            return False, f"Gender mismatch: scheme is for {scheme_gender.capitalize()} only"

    # 6. STATE -- HARD gate: only user's state or national schemes
    user_state = _lower(_g(user, "state"))
    scheme_state = _lower(_g(scheme, "state"), "all")
    if scheme_state not in NATIONAL_STATES and user_state and scheme_state != user_state:
        return False, (
            f"State mismatch: scheme is for {scheme_state.title()} only, "
            f"you are from {user_state.title()}"
        )

    # 7. DISABILITY
    scheme_dis = _g(scheme, "requires_disability", False)
    user_dis = _g(user, "is_disabled", False)
    if isinstance(user_dis, str):
        user_dis = user_dis.lower() in ("true", "1", "yes", "on")
    if scheme_dis and not user_dis:
        return False, "Scheme requires disability certificate"

    return True, ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STAGE 2: SOFT SCORING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _soft_score(user, scheme) -> tuple[int, list[str], list[str]]:
    """
    Score a scheme that already passed the hard filter.
    Returns (score, reasons, missing_documents).
    """
    score = 0
    reasons = []
    missing_docs = []

    user_edu = _edu_int(_g(user, "education_level"))
    user_label = _edu_label_for_user(user_edu)

    # ── EDUCATION (4 pts — always awarded, passed hard filter) ───────────────
    score += 4
    reasons.append(f"Eligible for your education level ({user_label})")

    # ── CATEGORY (2 pts — always awarded, passed hard filter) ────────────────
    scheme_cat = _lower(_g(scheme, "category"), "all")
    user_cat = _lower(_g(user, "category"), "all")
    if scheme_cat in ("all", ""):
        score += 2
        reasons.append("Open to all categories")
    else:
        score += 2
        reasons.append(f"Category matched ({user_cat.upper()})")

    # ── INCOME (2 pts — soft) ────────────────────────────────────────────────
    income = _safe_int(_g(user, "income"), 0)
    max_inc = _safe_int(_g(scheme, "max_income"))
    min_inc = _safe_int(_g(scheme, "min_income"))

    if max_inc is not None and income > max_inc:
        reasons.append(
            f"Income ({income:,}) slightly above preferred limit ({max_inc:,})"
        )
    elif min_inc is not None and income < min_inc:
        reasons.append(
            f"Income ({income:,}) below preferred minimum ({min_inc:,})"
        )
    else:
        score += 2
        if max_inc is None and min_inc is None:
            reasons.append("No income restriction")
        else:
            reasons.append("Income within eligible range")

    # ── STATE (passed hard filter -- add reason) ---------------------------------
    user_state = _lower(_g(user, "state"))
    scheme_state = _lower(_g(scheme, "state"), "all")
    if scheme_state in NATIONAL_STATES:
        reasons.append("National scheme (all states)")
    else:
        reasons.append(f"State matched ({user_state.title()})")

    # ── DOCUMENTS (1 pt — soft) ──────────────────────────────────────────────
    req_docs = _g(scheme, "required_documents", []) or []
    user_docs = _g(user, "available_documents", []) or []
    if isinstance(req_docs, str):
        req_docs = [d.strip() for d in req_docs.split(",") if d.strip()]
    if isinstance(user_docs, str):
        user_docs = [d.strip() for d in user_docs.split(",") if d.strip()]

    def normalize(text):
        """Deep normalization for fuzzy matching."""
        if not text: return ""
        t = str(text).lower().strip()
        t = re.sub(r"[^a-z0-9]", "", t)  # remove all non-alphanumeric
        # Handle specific common variations
        t = t.replace("aadhaar", "aadhar")
        t = t.replace("mark sheet", "marksheet")
        t = t.replace("marksheets", "marksheet")
        return t

    user_docs_normalized = {normalize(d) for d in user_docs if d}
    
    for doc in req_docs:
        norm_req = normalize(doc)
        if not norm_req: continue
        
        # 1. Direct normalized match
        if norm_req in user_docs_normalized:
            continue
            
        # 2. Substring match (e.g. "marksheet" in "10th marksheet")
        matched_fuzzy = False
        for ud_norm in user_docs_normalized:
            if ud_norm and (norm_req in ud_norm or ud_norm in norm_req):
                matched_fuzzy = True
                break
        
        if not matched_fuzzy:
            missing_docs.append(doc)

    if not missing_docs:
        score += 1
        if req_docs:
            reasons.append("All required documents available")
        else:
            reasons.append("No documents required")
    else:
        reasons.append(f"Missing documents: {', '.join(missing_docs)}")

    # ── AGE (1 pt — soft bonus) ──────────────────────────────────────────────
    user_age = _safe_int(_g(user, "age"), 0)
    scheme_min_age = _safe_int(_g(scheme, "min_age"))
    scheme_max_age = _safe_int(_g(scheme, "max_age"))

    if user_age > 0:
        age_ok = True
        if scheme_min_age is not None and user_age < scheme_min_age:
            reasons.append(f"Age ({user_age}) below preferred minimum ({scheme_min_age})")
            age_ok = False
        if scheme_max_age is not None and user_age > scheme_max_age:
            reasons.append(f"Age ({user_age}) above preferred maximum ({scheme_max_age})")
            age_ok = False
        if age_ok:
            score += 1
            reasons.append("Age within eligible range")
    else:
        score += 1  # No age info provided — grant point

    # ── Deadline proximity warning ───────────────────────────────────────────
    dl_raw = _g(scheme, "deadline", None)
    if dl_raw:
        try:
            dl = dl_raw if isinstance(dl_raw, datetime.date) else \
                datetime.datetime.strptime(str(dl_raw), "%Y-%m-%d").date()
            days_left = (dl - _today()).days
            if 0 <= days_left <= 15:
                reasons.append(f"Deadline approaching: {days_left} day(s) left!")
        except ValueError:
            pass

    return score, reasons, missing_docs


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PUBLIC API (used by views.py and tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calculate_match_score(user, scheme):
    """
    Full pipeline: hard filter → soft score.
    Returns (score, reasons, missing_documents, status).
    score = 0 means hard-reject.
    """
    passed, reject_reason = _hard_filter(user, scheme)
    if not passed:
        return 0, [reject_reason], [], "Ineligible"

    score, reasons, missing_docs = _soft_score(user, scheme)

    if score >= 9:
        status = "Highly Eligible"
    elif score >= 7:
        status = "Eligible"
    elif score >= 4:
        status = "Partially Eligible"
    else:
        status = "Low Match"

    return score, reasons, missing_docs, status


def get_best_schemes(user, schemes, min_score: int = 4) -> list[dict]:
    """
    Run the two-stage pipeline on all schemes.
    Returns results sorted by score DESC.
    Fallback: if nothing >= min_score, return top 5 closest (score > 0).
    NEVER returns empty if there are any potential matches.
    """
    all_passed = []
    total = 0
    rejected = 0

    for scheme in schemes:
        total += 1
        score, reasons, missing_docs, status = calculate_match_score(user, scheme)

        if score > 0:
            # Deadline proximity flag for template
            is_expiring_soon = any("Deadline approaching" in r for r in reasons)

            all_passed.append({
                "scheme":            _g(scheme, "name", "Unknown") or "Unknown",
                "score":             score,
                "reasons":           reasons,
                "missing_documents": missing_docs,
                "status":            status,
                "type":              _g(scheme, "opportunity_type", "") or "",
                "provider":          _g(scheme, "provider",         "") or "",
                "description":       _g(scheme, "description",      "") or "",
                "benefits":          _g(scheme, "benefits",         "") or "",
                "source":            str(_g(scheme, "source",   "") or ""),
                "deadline":          str(_g(scheme, "deadline", "") or ""),
                "is_expiring_soon":  is_expiring_soon,
                "state":             _g(scheme, "state", "All"),
                "category":          _g(scheme, "category", "All"),
                "gender":            _g(scheme, "gender", "All"),
            })
        else:
            rejected += 1

    # Sort by score descending
    all_passed.sort(key=lambda x: x["score"], reverse=True)

    # Primary: schemes above quality threshold
    qualified = [r for r in all_passed if r["score"] >= min_score]

    # Fallback: if nothing qualifies, return top 5 closest matches
    if qualified:
        final = qualified
        fallback_used = False
    elif all_passed:
        final = all_passed[:5]
        fallback_used = True
    else:
        final = []
        fallback_used = False

    logger.info(
        "[MATCHER] Total=%d | Passed=%d | Qualified(>=%d)=%d | Rejected=%d | Fallback=%s",
        total, len(all_passed), min_score, len(qualified), rejected, fallback_used,
    )
    print(
        f"[MATCHER] Total={total} | Passed={len(all_passed)} | "
        f"Qualified={len(qualified)} | Rejected={rejected} | Fallback={fallback_used}"
    )

    return final
