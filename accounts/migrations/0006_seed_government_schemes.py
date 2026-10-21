
from django.db import migrations


def add_government_schemes(apps, schema_editor):
    GovernmentScheme = apps.get_model(
        "accounts",
        "GovernmentScheme",
    )

    database = schema_editor.connection.alias

    schemes = [
        {
            "name": "National Scholarship Portal (NSP)",
            "slug": "nsp-scholarship",
            "category": "Education",
            "description": (
                "A portal for discovering and applying for "
                "government scholarship schemes."
            ),
            "eligibility": (
                "Students may qualify depending on the scholarship, "
                "academic course, income limits, and other conditions."
            ),
            "benefits": (
                "Scholarship assistance according to the selected "
                "scheme's rules."
            ),
            "official_url": "https://scholarships.gov.in/",
            "min_age": 0,
            "max_age": 120,
            "max_annual_income": None,
            "required_occupation": "student",
            "required_state": "",
            "requires_land_ownership": False,
            "requires_no_pucca_house": False,
        },
        {
            "name": "PM-KISAN",
            "slug": "pm-kisan",
            "category": "Agriculture",
            "description": (
                "A government income-support scheme for eligible "
                "landholding farmer families."
            ),
            "eligibility": (
                "Eligibility depends on landholding, exclusion "
                "criteria, and the official scheme guidelines."
            ),
            "benefits": (
                "Eligible farmer families may receive financial "
                "assistance under the scheme."
            ),
            "official_url": "https://pmkisan.gov.in/",
            "min_age": 18,
            "max_age": 120,
            "max_annual_income": None,
            "required_occupation": "farmer",
            "required_state": "",
            "requires_land_ownership": True,
            "requires_no_pucca_house": False,
        },
        {
            "name": "Ayushman Bharat PM-JAY",
            "slug": "ayushman-bharat-pmjay",
            "category": "Healthcare",
            "description": (
                "A public health assurance scheme for eligible "
                "families under the applicable guidelines."
            ),
            "eligibility": (
                "Eligibility depends on the applicable beneficiary "
                "criteria and official records. Check the official "
                "portal to confirm eligibility."
            ),
            "benefits": (
                "Eligible beneficiaries can access covered "
                "hospitalisation services under scheme rules."
            ),
            "official_url": "https://beneficiary.nha.gov.in/",
            "min_age": 0,
            "max_age": 120,
            "max_annual_income": None,
            "required_occupation": "",
            "required_state": "",
            "requires_land_ownership": False,
            "requires_no_pucca_house": False,
        },
        {
            "name": "Pradhan Mantri Awas Yojana (PMAY)",
            "slug": "pmay-housing",
            "category": "Housing",
            "description": (
                "Housing assistance under the applicable "
                "Pradhan Mantri Awas Yojana guidelines."
            ),
            "eligibility": (
                "Eligibility depends on the relevant PMAY component, "
                "housing status, income category, and other rules."
            ),
            "benefits": (
                "Eligible beneficiaries may receive housing "
                "assistance according to the scheme guidelines."
            ),
            "official_url": "https://pmay-urban.gov.in/",
            "min_age": 18,
            "max_age": 120,
            "max_annual_income": None,
            "required_occupation": "",
            "required_state": "",
            "requires_land_ownership": False,
            "requires_no_pucca_house": True,
        },
    ]

    for scheme in schemes:
        GovernmentScheme.objects.using(database).get_or_create(
            slug=scheme["slug"],
            defaults=scheme,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_governmentscheme_requires_land_ownership_and_more"),
    ]

    operations = [
        migrations.RunPython(
            add_government_schemes,
            migrations.RunPython.noop,
        ),
    ]
