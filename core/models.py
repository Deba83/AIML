from django.db import models

# ==============================
# EDUCATION LEVEL NUMERIC MAP
# ==============================
# under_10=0  10th=1  12th=2  diploma/ITI=3  UG=4  PG=5
EDUCATION_LEVEL_CHOICES = [
    (0, 'Under 10th'),
    (1, '10th Pass'),
    (2, '12th Pass'),
    (3, 'Diploma / ITI'),
    (4, 'Undergraduate (UG)'),
    (5, 'Postgraduate (PG)'),
]

EDU_LABEL_MAP = {
    0: 'Under 10th',
    1: '10th',
    2: '12th',
    3: 'Diploma/ITI',
    4: 'UG',
    5: 'PG',
}

# ==============================
# Education level for DRF / UserProfile / Scheme matching
# (string keys map to numeric codes above)
# ==============================
EDU_STRING_CHOICES = [
    ('school',  'School (Under 10th)'),
    ('10th',    '10th Pass'),
    ('12th',    '12th / Higher Secondary'),
    ('diploma', 'Diploma / ITI'),
    ('ug',      'Undergraduate (UG)'),
    ('pg',      'Postgraduate (PG)'),
]

CATEGORY_CHOICES = [
    ('general', 'General'),
    ('obc',     'OBC'),
    ('sc',      'SC'),
    ('st',      'ST'),
    ('ews',     'EWS'),
    ('all',     'All'),
]


class Scheme(models.Model):
    TYPE_CHOICES = [
        ('scheme',      'Scheme'),
        ('scholarship', 'Scholarship'),
        ('internship',  'Internship'),
        ('fellowship',  'Fellowship'),
    ]
    PROVIDER_CHOICES = [
        ('govt',    'Government'),
        ('private', 'Private'),
        ('ngo',     'NGO'),
    ]

    name             = models.CharField(max_length=255)
    scheme_code      = models.CharField(max_length=80, unique=True, blank=True, null=True,
                           help_text="Unique identifier for deduplication (auto-set if blank)")
    opportunity_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='scheme')
    provider         = models.CharField(max_length=10, choices=PROVIDER_CHOICES, default='govt')
    description      = models.TextField(blank=True, null=True)
    benefits         = models.TextField(blank=True, null=True,
                           help_text="What the beneficiary receives (e.g., INR 5000/month, free LPG cylinder)")

    # ── Income eligibility ──────────────────────────────────────────────
    min_income  = models.IntegerField(null=True, blank=True, help_text="Minimum annual income (INR). NULL = no lower bound.")
    max_income  = models.IntegerField(null=True, blank=True, help_text="Maximum annual income (INR). NULL = no upper limit.")

    # ── Education eligibility (numeric codes 0–5) ───────────────────────
    education_min = models.IntegerField(default=0, choices=EDUCATION_LEVEL_CHOICES)
    education_max = models.IntegerField(default=5, choices=EDUCATION_LEVEL_CHOICES)

    # ── Other eligibility ───────────────────────────────────────────────
    category          = models.CharField(max_length=50, default='all')
    state             = models.CharField(max_length=100, default='all')
    gender            = models.CharField(max_length=20, default='All')
    requires_disability = models.BooleanField(default=False)
    min_marks         = models.FloatField(null=True, blank=True,
                            help_text="Minimum academic percentage/CGPA*10 required (optional)")

    # ── Production metadata ─────────────────────────────────────────────
    required_documents = models.JSONField(default=list, blank=True)
    deadline           = models.DateField(blank=True, null=True)
    source             = models.URLField(max_length=500, blank=True, null=True)
    last_updated       = models.DateTimeField(auto_now=True)
    required_skill     = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.get_opportunity_type_display()})"

    class Meta:
        verbose_name        = "Scheme / Opportunity"
        verbose_name_plural = "Schemes & Opportunities"
        ordering            = ['name']


class UserProfile(models.Model):
    """
    Persisted user query profile — created each time someone hits POST /api/match-schemes/.
    Useful for analytics and re-querying without re-entering data.
    """
    name            = models.CharField(max_length=255)
    income          = models.IntegerField(help_text="Annual income in INR")
    education_level = models.CharField(max_length=20, choices=EDU_STRING_CHOICES,
                          help_text="Use: school | 10th | 12th | diploma | ug | pg")
    category        = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    state           = models.CharField(max_length=100)
    marks           = models.FloatField(null=True, blank=True,
                          help_text="Percentage (0–100). For CGPA multiply by 10.")
    gender          = models.CharField(max_length=20, default='All')
    is_disabled     = models.BooleanField(default=False)
    available_documents = models.JSONField(default=list, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.education_level}, {self.state})"

class UndoLog(models.Model):
    action = models.CharField(max_length=10)  # create/update/delete
    object_id = models.IntegerField()
    model_name = models.CharField(max_length=50)
    previous_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action.upper()} on {self.model_name}:{self.object_id} at {self.created_at}"

    class Meta:
        verbose_name = "Undo Log"
        verbose_name_plural = "Undo Logs"
        ordering = ['-created_at']
