
from django.db import migrations


def create_demo_alerts(apps, schema_editor):
    SchemeAlert = apps.get_model("accounts", "SchemeAlert")

    alerts = [
        {
            "title": "Demo: Scholarship Scheme Alert",
            "category": "Education",
            "message": (
                "DEMO NOTIFICATION: Students can check scholarship "
                "opportunities and eligibility criteria on the official "
                "National Scholarship Portal. Verify deadlines and "
                "requirements before applying."
            ),
        },
        {
            "title": "Demo: Farmer Scheme Information",
            "category": "Agriculture",
            "message": (
                "DEMO NOTIFICATION: Farmers can review PM-KISAN scheme "
                "information on the official government portal. Verify "
                "current eligibility and application requirements."
            ),
        },
        {
            "title": "Demo: Healthcare Scheme Information",
            "category": "Healthcare",
            "message": (
                "DEMO NOTIFICATION: Citizens can review healthcare "
                "scheme information through the official government "
                "beneficiary portal and check current eligibility."
            ),
        },
    ]

    for alert in alerts:
        SchemeAlert.objects.get_or_create(
            title=alert["title"],
            defaults={
                "category": alert["category"],
                "message": alert["message"],
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_add_demo_scheme_alerts"),
    ]

    operations = [
        migrations.RunPython(
            create_demo_alerts,
            migrations.RunPython.noop,
        ),
    ]
