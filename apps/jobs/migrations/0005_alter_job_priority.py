from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0004_job_priority_ctc_skills"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="priority",
            field=models.CharField(
                choices=[
                    ("P0", "P0 — Critical (Hire Immediately)"),
                    ("P1", "P1 — High priority"),
                    ("P2", "P2 — Moderate priority"),
                    ("P3", "P3 — Low priority (Backlog)"),
                ],
                default="P2",
                max_length=2,
            ),
        ),
    ]
