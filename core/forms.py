from django import forms

class EligibilityForm(forms.Form):
    age = forms.IntegerField(min_value=1, max_value=120, required=True, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter age'}))
    income = forms.IntegerField(min_value=1, required=True, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Annual Income in INR'}))
    category = forms.ChoiceField(
        choices=[('', 'Select Category'), ('General', 'General'), ('OBC', 'OBC'), ('SC', 'SC'), ('ST', 'ST'), ('EWS', 'EWS')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    gender = forms.ChoiceField(
        choices=[('', 'Select Gender'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    area = forms.ChoiceField(
        choices=[('', 'Select Area'), ('Rural', 'Rural'), ('Urban', 'Urban')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    occupation = forms.ChoiceField(
        choices=[('', 'Select Occupation'), ('Student', 'Student'), ('Farmer', 'Farmer'), ('Unemployed', 'Unemployed'), ('Business Owner', 'Business Owner'), ('Employed', 'Employed')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    family_income_type = forms.ChoiceField(
        choices=[('', 'Select Income Type'), ('BPL', 'BPL (Below Poverty Line)'), ('APL', 'APL (Above Poverty Line)'), ('Middle', 'Middle Class')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_disabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    education_level = forms.ChoiceField(
        label='Highest Education Level',
        choices=[('', 'Select Education'), ('under_10', 'Under 10th'), ('10th', '10th'), ('12th', '12th'), ('diploma', 'Diploma'), ('iti', 'ITI'), ('ug', 'Undergraduate (UG)'), ('pg', 'Postgraduate (PG)')],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'highestEdu', 'onchange': 'handleEducationFlow()'})
    )
    stream = forms.ChoiceField(
        label='Course / Stream',
        choices=[('', 'Select Stream'), ('Engineering', 'Engineering'), ('Medical', 'Medical'), ('Commerce', 'Commerce'), ('Arts', 'Arts'), ('Science', 'Science')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    branch = forms.ChoiceField(
        choices=[('', 'Select Branch'), ('Computer Science', 'Computer Science'), ('Mechanical', 'Mechanical'), ('Civil', 'Civil'), ('Electrical', 'Electrical'), ('Electronics', 'Electronics'), ('AI/ML', 'AI/ML')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    year = forms.IntegerField(min_value=1, max_value=7, required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Year of Study (e.g. 1)'}))
    
    # Progressive Education Marks
    marks_10th = forms.FloatField(min_value=0.0, max_value=100.0, required=False, label="10th Percentage (%)", widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '%', 'step': '0.01'}))
    marks_12th = forms.FloatField(min_value=0.0, max_value=100.0, required=False, label="12th Percentage (%)", widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '%', 'step': '0.01'}))
    cgpa_ug = forms.FloatField(min_value=0.0, max_value=10.0, required=False, label="UG CGPA", widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'CGPA (Out of 10)', 'step': '0.01'}))
    cgpa_pg = forms.FloatField(min_value=0.0, max_value=10.0, required=False, label="PG CGPA", widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'CGPA (Out of 10)', 'step': '0.01'}))
    
    skills = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Python, Data Entry, Accounting'}))
    experience = forms.IntegerField(min_value=0, required=False, label="Experience (Months)", widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Months'}))
    state = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your State'}))
    is_entrepreneur = forms.BooleanField(required=False, label="I am looking for Business / Startup Schemes", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    # Document Checkboxes
    aadhaar = forms.BooleanField(required=False, label="Aadhaar Card", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    income_cert = forms.BooleanField(required=False, label="Income Certificate", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    caste_cert = forms.BooleanField(required=False, label="Caste Certificate", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    domicile = forms.BooleanField(required=False, label="Domicile Certificate", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    marksheet = forms.BooleanField(required=False, label="Marksheet", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    bank_passbook = forms.BooleanField(required=False, label="Bank Passbook", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    resume = forms.BooleanField(required=False, label="Resume / CV", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    disability_cert = forms.BooleanField(required=False, label="Disability Certificate", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    transcripts = forms.BooleanField(required=False, label="Transcripts", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    land_record = forms.BooleanField(required=False, label="Land Record", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    business_plan = forms.BooleanField(required=False, label="Business Plan / Project Report", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    pan_card = forms.BooleanField(required=False, label="PAN Card", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    ration_card = forms.BooleanField(required=False, label="Ration Card", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    minority_cert = forms.BooleanField(required=False, label="Minority Certificate", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    admission_letter = forms.BooleanField(required=False, label="Admission Letter", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    experience_cert = forms.BooleanField(required=False, label="Experience Certificate", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    death_cert = forms.BooleanField(required=False, label="Death Certificate (Parent)", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    def clean_age(self):
        age = self.cleaned_data.get('age')
        if age is None or age <= 0:
            raise forms.ValidationError("Age must be greater than 0.")
        return age

    def clean_income(self):
        income = self.cleaned_data.get('income')
        if income is None or income <= 0:
            raise forms.ValidationError("Income must be greater than 0.")
        return income
