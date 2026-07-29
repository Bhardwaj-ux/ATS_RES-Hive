# FILEPATH: apps/jobs/forms.py
from django import forms
from .models import Job

CITY_CHOICES = [
    ("", "Select a city"),
    ("Bengaluru", "Bengaluru"),
    ("Gurugram", "Gurugram"),
    ("Delhi", "Delhi"),
]


class JobForm(forms.ModelForm):
    location = forms.ChoiceField(choices=CITY_CHOICES, required=False, label="City")

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
            "requirements",
            "description",
            "status",
        ]
        labels = {
            "employment_type": "Job Type",
            "requirements": "Key Responsibilities",
            "description": "Description of Job",
            "required_skills": "Skills",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "requirements": forms.Textarea(
                attrs={"rows": 6, "id": "id_requirements_richtext_source"}
            ),
            "required_skills": forms.HiddenInput(),
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

    def clean_required_skills(self):
        raw_value = (self.cleaned_data.get("required_skills") or "").strip()
        parts = raw_value.replace("\n", ",").split(",")
        cleaned = []
        seen = set()
        for part in parts:
            skill = part.lower().strip()
            if not skill or skill in seen:
                continue
            seen.add(skill)
            cleaned.append(skill)
        return ", ".join(cleaned)
