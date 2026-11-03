from django.core.management.base import BaseCommand
from core.models import Scheme
import datetime

class Command(BaseCommand):
    help = 'Loads sample data using unified Scheme model with strict numeric education codes'

    # Education codes: under_10=0  10th=1  12th=2  diploma/ITI=3  UG=4  PG=5

    SAMPLE_DATA = [
        # ---- SCHEMES ----
        {
            "name": "PM Awas Yojana",
            "opportunity_type": "scheme", "provider": "govt",
            "education_min": 0, "education_max": 5,      # open to all
            "max_income": 300000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Income Certificate", "Domicile Certificate"],
            "deadline": "2026-12-31", "source": "https://pmaymis.gov.in",
            "description": "Housing for all by providing subsidies to eligible beneficiaries.",
        },
        {
            "name": "Ayushman Bharat",
            "opportunity_type": "scheme", "provider": "govt",
            "education_min": 0, "education_max": 5,
            "max_income": 500000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Income Certificate"],
            "deadline": "2026-12-31", "source": "https://pmjay.gov.in",
            "description": "Health coverage of up to INR 5 lakh per family per year.",
        },
        {
            "name": "PM Kisan Samman Nidhi",
            "opportunity_type": "scheme", "provider": "govt",
            "education_min": 0, "education_max": 5,
            "max_income": 200000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Land Record"],
            "deadline": "2026-12-31", "source": "https://pmkisan.gov.in",
            "description": "Direct income support of INR 6000/year to eligible farmer families.",
        },
        {
            "name": "Skill India Program",
            "opportunity_type": "scheme", "provider": "govt",
            "education_min": 0, "education_max": 3,      # up to Diploma/ITI
            "max_income": 500000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar"],
            "deadline": "2026-12-31", "source": "https://www.skillindiadigital.gov.in",
            "description": "Skill development training for youth to improve employability.",
        },
        {
            "name": "PM Ujjwala Yojana",
            "opportunity_type": "scheme", "provider": "govt",
            "education_min": 0, "education_max": 5,
            "max_income": 200000, "category": "All", "state": "All",
            "gender": "Female", "requires_disability": False,
            "required_documents": ["Aadhaar", "Income Certificate"],
            "deadline": "2026-12-31", "source": "https://www.pmuy.gov.in",
            "description": "Free LPG connections to women from BPL households.",
        },
        {
            "name": "Stand-Up India Scheme",
            "opportunity_type": "scheme", "provider": "govt",
            "education_min": 0, "education_max": 5,
            "max_income": 1000000, "category": "SC", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Business Plan / Project Report"],
            "deadline": "2026-12-31", "source": "https://www.standupmitra.in",
            "description": "Bank loans between INR 10 lakh and 1 crore for SC/ST and women entrepreneurs.",
        },
        {
            "name": "Disability Pension Scheme",
            "opportunity_type": "scheme", "provider": "govt",
            "education_min": 0, "education_max": 5,
            "max_income": 150000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": True,
            "required_documents": ["Aadhaar", "Disability Certificate"],
            "deadline": "2026-12-31", "source": "https://nsap.nic.in",
            "description": "Monthly pension assistance to persons with severe disabilities.",
        },
        {
            "name": "PM Mudra Yojana",
            "opportunity_type": "scheme", "provider": "govt",
            "education_min": 0, "education_max": 5,
            "max_income": 1000000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Business Plan / Project Report"],
            "deadline": "2026-12-31", "source": "https://www.mudra.org.in",
            "description": "Micro-finance loans up to INR 10 lakh for small businesses.",
        },

        # ---- SCHOLARSHIPS ----
        {
            "name": "Pre-Matric Scholarship (NSP)",
            "opportunity_type": "scholarship", "provider": "govt",
            "education_min": 0, "education_max": 0,      # Under 10th only
            "max_income": 100000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Income Certificate", "Marksheet"],
            "deadline": "2026-10-31", "source": "https://scholarships.gov.in",
            "description": "Scholarship for students from minority communities in class 1–10.",
        },
        {
            "name": "Post-Matric Scholarship (NSP)",
            "opportunity_type": "scholarship", "provider": "govt",
            "education_min": 1, "education_max": 5,      # 10th pass to PG
            "max_income": 250000, "category": "SC",    "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Income Certificate", "Caste Certificate", "Marksheet"],
            "deadline": "2026-11-30", "source": "https://scholarships.gov.in",
            "description": "Post-matric scholarship for SC students studying outside their home state.",
        },
        {
            "name": "Central Sector Scholarship for College Students (NSP)",
            "opportunity_type": "scholarship", "provider": "govt",
            "education_min": 4, "education_max": 5,      # UG to PG
            "max_income": 450000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Income Certificate", "Marksheet"],
            "deadline": "2026-11-30", "source": "https://scholarships.gov.in",
            "description": "Financial assistance to meritorious students from low-income families.",
        },
        {
            "name": "National Means-cum-Merit Scholarship (NMMS)",
            "opportunity_type": "scholarship", "provider": "govt",
            "education_min": 1, "education_max": 1,      # 10th only
            "max_income": 350000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Marksheet", "Income Certificate"],
            "deadline": "2026-06-30", "source": "https://scholarships.gov.in",
            "description": "Scholarship for meritorious students of economically weaker sections at 10th level.",
        },
        {
            "name": "INSPIRE Scholarship",
            "opportunity_type": "scholarship", "provider": "govt",
            "education_min": 2, "education_max": 4,      # 12th to UG
            "max_income": 800000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Marksheet"],
            "deadline": "2026-10-31", "source": "https://online-inspire.gov.in",
            "description": "Scholarship for top 1% students in 12th board exams pursing science at UG level.",
        },
        {
            "name": "AICTE Pragati Scholarship for Girls",
            "opportunity_type": "scholarship", "provider": "govt",
            "education_min": 3, "education_max": 3,      # Diploma only
            "max_income": 800000, "category": "All", "state": "All",
            "gender": "Female", "requires_disability": False,
            "required_documents": ["Aadhaar", "Income Certificate", "Marksheet"],
            "deadline": "2026-12-15", "source": "https://www.aicte-india.org/",
            "description": "Financial assistance for girls pursuing Diploma-level technical education.",
        },
        {
            "name": "AICTE Saksham Scholarship",
            "opportunity_type": "scholarship", "provider": "govt",
            "education_min": 3, "education_max": 3,      # Diploma only
            "max_income": 800000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": True,
            "required_documents": ["Aadhaar", "Income Certificate", "Disability Certificate", "Marksheet"],
            "deadline": "2026-12-15", "source": "https://www.aicte-india.org/",
            "description": "Scholarship for specially-abled students pursuing Diploma-level technical education.",
        },
        {
            "name": "Reliance Foundation Scholarship",
            "opportunity_type": "scholarship", "provider": "private",
            "education_min": 4, "education_max": 4,      # UG only
            "max_income": 1500000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Marksheet", "Transcripts"],
            "deadline": "2026-02-28", "source": "https://scholarships.reliancefoundation.org",
            "description": "Scholarship for bright young undergraduates to unlock their potential.",
        },

        # ---- INTERNSHIPS ----
        {
            "name": "NITI Aayog Internship",
            "opportunity_type": "internship", "provider": "govt",
            "education_min": 4, "education_max": 5,      # UG to PG
            "max_income": 10000000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Resume / CV"],
            "deadline": "2026-12-31", "source": "https://www.niti.gov.in/internship",
            "description": "Internship program at India's premier policy think tank.",
        },
        {
            "name": "Digital India Internship",
            "opportunity_type": "internship", "provider": "govt",
            "education_min": 4, "education_max": 5,
            "max_income": 10000000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Resume / CV"],
            "deadline": "2026-12-31", "source": "https://dii.nic.in",
            "description": "Internship under Ministry of Electronics and IT for tech-oriented students.",
        },
        {
            "name": "ISRO Internship",
            "opportunity_type": "internship", "provider": "govt",
            "education_min": 3, "education_max": 5,      # Diploma to PG
            "max_income": 10000000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Resume / CV", "Transcripts"],
            "deadline": "2026-12-31", "source": "https://www.isro.gov.in",
            "description": "Research internship at Indian Space Research Organisation.",
        },
        {
            "name": "Google Summer of Code (GSoC)",
            "opportunity_type": "internship", "provider": "private",
            "education_min": 4, "education_max": 5,      # UG to PG
            "max_income": 10000000, "category": "All", "state": "All",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Resume / CV"],
            "deadline": "2026-04-15", "source": "https://summerofcode.withgoogle.com/",
            "description": "Global open source software development program for students.",
        },

        # ---- ODISHA-SPECIFIC ----
        {
            "name": "Odisha State Post-Matric Scholarship",
            "opportunity_type": "scholarship", "provider": "govt",
            "education_min": 1, "education_max": 5,      # 10th -> PG (post-matric)
            "max_income": 250000, "category": "All", "state": "Odisha",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Income Certificate", "Caste Certificate", "Domicile Certificate"],
            "deadline": "2026-09-30", "source": "https://scholarship.odisha.gov.in/",
            "description": "For ST/SC/OBC/SEBC/EBC students at post-matric stage in Odisha.",
        },
        {
            "name": "KALIA Scholarship (Odisha)",
            "opportunity_type": "scholarship", "provider": "govt",
            "education_min": 4, "education_max": 5,      # UG to PG only
            "max_income": 10000000, "category": "All", "state": "Odisha",
            "gender": "All", "requires_disability": False,
            "required_documents": ["Aadhaar", "Income Certificate", "Domicile Certificate", "Bank Passbook"],
            "deadline": "2026-08-31", "source": "https://kalia.odisha.gov.in/",
            "description": "Educational support for children of KALIA beneficiary farmer families.",
        },
    ]

    def handle(self, *args, **kwargs):
        # Ensure admin user exists
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write("Superuser 'admin' created (password: admin123)")

        self.stdout.write("Clearing existing scheme data...")
        Scheme.objects.all().delete()

        self.stdout.write(f"Loading {len(self.SAMPLE_DATA)} opportunities...")
        created = 0
        errors = 0

        for item in self.SAMPLE_DATA:
            try:
                # Validate education codes
                edu_min = item['education_min']
                edu_max = item['education_max']
                assert 0 <= edu_min <= 5, f"edu_min={edu_min} out of range"
                assert 0 <= edu_max <= 5, f"edu_max={edu_max} out of range"
                assert edu_min <= edu_max,  f"edu_min({edu_min}) > edu_max({edu_max})"

                deadline_val = None
                if item.get('deadline'):
                    deadline_val = datetime.date.fromisoformat(item['deadline'])

                Scheme.objects.create(
                    name=item['name'],
                    opportunity_type=item['opportunity_type'],
                    provider=item['provider'],
                    education_min=edu_min,
                    education_max=edu_max,
                    max_income=item.get('income_limit', 10000000),
                    category=item.get('category', 'All'),
                    state=item.get('state', 'All'),
                    gender=item.get('gender', 'All'),
                    requires_disability=item.get('requires_disability', False),
                    required_documents=item.get('required_documents', []),
                    deadline=deadline_val,
                    source=item.get('source', ''),
                    description=item.get('description', ''),
                )
                created += 1
                self.stdout.write(
                    f"  [OK] {item['name']} | edu={edu_min}–{edu_max} | {item['opportunity_type']}"
                )
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"  [ERR] {item.get('name', '?')}: {e}"))

        # Report private count
        private_count = Scheme.objects.filter(provider='private').count()
        if private_count == 0:
            self.stdout.write(self.style.WARNING(
                "[PRIVATE=0] No private opportunities in DB — check SAMPLE_DATA."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created: {created}, Errors: {errors}, Private in DB: {private_count}"
        ))
