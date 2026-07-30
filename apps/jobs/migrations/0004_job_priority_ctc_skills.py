from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0003_alter_job_required_skills"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="skills_data",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="job",
            name="priority",
            field=models.CharField(
                choices=[
                    ("P0", "P0 — Critical, hire immediately"),
                    ("P1", "P1 — High priority"),
                    ("P2", "P2 — Moderate priority"),
                    ("P3", "P3 — Low priority / backlog"),
                ],
                default="P2",
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="ctc_mode",
            field=models.CharField(
                choices=[
                    ("range", "Range"),
                    ("negotiable", "Negotiable"),
                    ("hidden", "Do not mention"),
                ],
                default="hidden",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="ctc_min",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=6, null=True
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="ctc_max",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=6, null=True
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("open", "Open"),
                    ("closed", "Closed"),
                    ("on_hold", "Archived"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="employment_type",
            field=models.CharField(
                choices=[
                    ("full_time", "Full Time"),
                    ("part_time", "Part Time"),
                    ("intern", "Internship"),
                    ("contract", "Contract"),
                ],
                default="full_time",
                max_length=20,
            ),
        ),
    ]
