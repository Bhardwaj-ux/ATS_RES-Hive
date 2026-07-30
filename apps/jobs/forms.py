# FILEPATH: apps/jobs/forms.py
from django import forms
from .models import Job

CITY_CHOICES = [
    ("", "Select a city"),
    ("Bengaluru", "Bengaluru"),
    ("Gurugram", "Gurugram"),
    ("Delhi", "Delhi"),
]

DEPARTMENT_CHOICES = [("", "Select a department")] + list(Job.Department.choices)


class JobForm(forms.ModelForm):
    location = forms.ChoiceField(choices=CITY_CHOICES, required=False, label="City")
    department = forms.ChoiceField(
        choices=DEPARTMENT_CHOICES, required=True, label="Department"
    )

    class Meta:
        model = Job
        fields = [
            "title",
            "department",
            "location",
            "employment_type",
            "experience_min_years",
            "experience_max_years",
            "required_skills",
            "skills_data",
            "requirements",
            "description",
            "priority",
            "ctc_mode",
            "ctc_min",
            "ctc_max",
            "status",
        ]
        labels = {
            "employment_type": "Job Type",
            "requirements": "Roles & Responsibilities",
            "description": "Description of Job",
            "required_skills": "Skills",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "requirements": forms.Textarea(
                attrs={"rows": 6, "id": "id_requirements_richtext_source"}
            ),
            "required_skills": forms.HiddenInput(),
            "skills_data": forms.HiddenInput(),
            "ctc_mode": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_location = (
            self.initial.get("location") or getattr(self.instance, "location", "") or ""
        ).strip()
        if current_location and current_location not in dict(CITY_CHOICES):
            self.fields["location"].choices = CITY_CHOICES + [
                (current_location, current_location)
            ]
        self.fields["experience_min_years"].label = "Min"
        self.fields["experience_max_years"].label = "Max"
        self.fields["ctc_min"].required = False
        self.fields["ctc_max"].required = False

    def clean_required_skills(self):
        raw_value = (self.cleaned_data.get("required_skills") or "").strip()
        parts = raw_value.replace("\n", ",").split(",")
        cleaned = []
        seen = set()
        for part in parts:
            skill = part.strip()
            if not skill:
                continue
            key = skill.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(skill)
        return ", ".join(cleaned)

    def clean_skills_data(self):
        import json

        raw_value = self.cleaned_data.get("skills_data")
        if not raw_value:
            return []
        if isinstance(raw_value, list):
            return raw_value
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                return parsed
        except (ValueError, TypeError):
            pass
        return []
