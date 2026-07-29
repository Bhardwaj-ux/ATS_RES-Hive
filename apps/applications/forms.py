# FILEPATH: apps/applications/forms.py
from django import forms
from .models import Application


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = [
            "job",
            "full_name",
            "email",
            "phone",
            "current_location",
            "total_experience_years",
            "source",
            "status",
            "summary",
            "skills",
        ]
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 4}),
            "skills": forms.HiddenInput(attrs={"id": "id_skills_hidden"}),
        }

    def clean_skills(self):
        raw_value = (self.cleaned_data.get("skills") or "").strip()
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


class ApplicationStatusForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["status"]
