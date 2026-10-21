
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound
from django.urls import reverse

from .models import SchemeAlert, EligibilityHistory, GovernmentScheme


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not all([
            full_name, email, username, password, confirm_password
        ]):
            messages.error(request, "Please fill in all fields.")

        elif len(username) > 150:
            messages.error(
                request, "Username must be 150 characters or fewer."
            )

        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")

        elif len(password) < 8:
            messages.error(
                request, "Password must contain at least 8 characters."
            )

        elif User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Username already exists.")

        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email already registered.")

        else:
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name,
            )
            messages.success(
                request, "Registration successful! Please log in."
            )
            return redirect("accounts:login")

    return render(request, "accounts/register.html")


def user_login(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request, username=username, password=password
        )

        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect("accounts:home")

        messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login.html")


@login_required(login_url="accounts:login")
def user_logout(request):
    logout(request)
    messages.success(request, "You have logged out successfully.")
    return redirect("accounts:login")


@login_required(login_url="accounts:login")
def home(request):
    total_users = User.objects.count()
    total_schemes = GovernmentScheme.objects.count()
    total_checks = EligibilityHistory.objects.count()
    total_alerts = SchemeAlert.objects.count()

    my_total_checks = EligibilityHistory.objects.filter(
        user=request.user
    ).count()

    recent_checks = EligibilityHistory.objects.filter(
        user=request.user
    ).order_by("-checked_at")[:5]

    context = {
        "total_users": total_users,
        "total_schemes": total_schemes,
        "total_checks": total_checks,
        "total_alerts": total_alerts,
        "my_total_checks": my_total_checks,
        "recent_checks": recent_checks,
    }

    return render(request, "accounts/home.html", context)


@login_required(login_url="accounts:login")
def check_eligibility(request):
    if request.method == "GET":
        return render(
            request,
            "accounts/eligibility.html",
            {
                "result": "",
                "suggested_schemes": [],
            },
        )

    age_text = request.POST.get("age", "").strip()
    income_text = request.POST.get("income", "").strip()
    occupation = request.POST.get("occupation", "").strip().lower()
    state = request.POST.get("state", "").strip()
    student_status = request.POST.get(
        "student_status", ""
    ).strip().lower()
    farmer_status = request.POST.get(
        "farmer_status", ""
    ).strip().lower()
    land_ownership_status = request.POST.get(
        "land_ownership_status", ""
    ).strip().lower()
    housing_status = request.POST.get(
        "housing_status", ""
    ).strip().lower()
    pucca_house_status = request.POST.get(
        "pucca_house_status", ""
    ).strip().lower()

    if not all([
        age_text,
        income_text,
        occupation,
        state,
        student_status,
        farmer_status,
        land_ownership_status,
        housing_status,
        pucca_house_status,
    ]):
        return render(
            request,
            "accounts/eligibility.html",
            {
                "result": "Please complete all fields.",
                "suggested_schemes": [],
            },
        )

    try:
        age = int(age_text)
        income = int(income_text)
    except (ValueError, TypeError):
        return render(
            request,
            "accounts/eligibility.html",
            {
                "result": (
                    "Please enter valid whole numbers for age "
                    "and annual family income."
                ),
                "suggested_schemes": [],
            },
        )

    if not 1 <= age <= 120:
        result = "Please enter an age between 1 and 120."
    elif income < 0:
        result = "Annual family income cannot be negative."
    elif occupation not in {
        "student", "farmer", "employee", "unemployed", "self_employed"
    }:
        result = "Please select a valid occupation."
    elif student_status not in {"yes", "no"}:
        result = "Please select a valid student status."
    elif farmer_status not in {"yes", "no"}:
        result = "Please select a valid farmer status."
    elif land_ownership_status not in {"yes", "no"}:
        result = "Please select a valid land ownership answer."
    elif housing_status not in {"yes", "no"}:
        result = "Please select a valid housing status."
    elif pucca_house_status not in {"yes", "no"}:
        result = "Please select a valid pucca-house answer."
    else:
        result = ""
    
    if result:
        return render(
            request,
            "accounts/eligibility.html",
            {
                "result": result,
                "suggested_schemes": [],
            },
        )

    suggested_schemes = []

    for scheme in GovernmentScheme.objects.all().order_by("name"):
        matched = True
        category = (scheme.category or "").strip().casefold()
        required_occupation = (
            scheme.required_occupation or ""
        ).strip().casefold()
        required_state = (
            scheme.required_state or ""
        ).strip().casefold()

        # Age range
        if not scheme.min_age <= age <= scheme.max_age:
            matched = False

        # Maximum annual family income, if configured
        if (
            scheme.max_annual_income is not None
            and income > scheme.max_annual_income
        ):
            matched = False

        # Explicit occupation requirement
        if required_occupation and required_occupation != occupation:
            matched = False

        # Explicit state requirement
        if required_state and required_state != state.casefold():
            matched = False

        # Student requirements for education schemes
        if "education" in category and student_status != "yes":
            matched = False

        # Agriculture requirements
        if "agriculture" in category and (
            farmer_status != "yes"
            or occupation != "farmer"
            or land_ownership_status != "yes"
        ):
            matched = False

        if (
            scheme.requires_land_ownership
            and land_ownership_status != "yes"
        ):
            matched = False

        # Housing requirements
        if "housing" in category and housing_status != "yes":
            matched = False

        if (
            scheme.requires_no_pucca_house
            and pucca_house_status != "no"
        ):
            matched = False

        if matched:
            suggested_schemes.append(scheme)

    if suggested_schemes:
        result = (
            "The schemes below match your answers and the criteria "
            "configured in this portal. This is a preliminary screening, "
            "not official confirmation of eligibility. Verify official "
            "scheme rules before applying."
        )
    else:
        result = (
            "No schemes matched the configured criteria and your answers. "
            "You may still qualify for other schemes. Please check the "
            "official requirements."
        )

    # Save the result and redirect to prevent refresh from repeating POST.
    EligibilityHistory.objects.create(
        user=request.user,
        age=age,
        income=income,
        occupation=occupation,
        result=result,
    )

    request.session["eligibility_result"] = result
    request.session["eligibility_scheme_slugs"] = [
        scheme.slug for scheme in suggested_schemes
    ]

    return redirect("accounts:eligibility_result")


@login_required(login_url="accounts:login")
def eligibility_result(request):
    result = request.session.pop("eligibility_result", "")
    scheme_slugs = request.session.pop("eligibility_scheme_slugs", [])

    suggested_schemes = list(
        GovernmentScheme.objects.filter(
            slug__in=scheme_slugs
        ).order_by("name")
    )

    return render(
        request,
        "accounts/eligibility.html",
        {
            "result": result,
            "suggested_schemes": suggested_schemes,
        },
    )


@login_required(login_url="accounts:login")
def schemes(request):
    scheme_list = GovernmentScheme.objects.all().order_by("name")

    return render(
        request,
        "accounts/schemes.html",
        {"schemes": scheme_list},
    )


@login_required(login_url="accounts:login")
def live_alerts(request):
    alerts = SchemeAlert.objects.all().order_by("-created_at")

    return render(
        request,
        "accounts/alerts.html",
        {"alerts": alerts},
    )


@login_required(login_url="accounts:login")
def user_profile(request):
    return render(
        request,
        "accounts/profile.html",
        {"profile_user": request.user},
    )


@login_required(login_url="accounts:login")
def eligibility_history(request):
    history = EligibilityHistory.objects.filter(
        user=request.user
    ).order_by("-checked_at")

    return render(
        request,
        "accounts/history.html",
        {"history": history},
    )


@login_required(login_url="accounts:login")
def scheme_details(request, scheme_name):
    scheme = GovernmentScheme.objects.filter(
        slug=scheme_name
    ).first()

    if scheme is None:
        return HttpResponseNotFound(
            "Scheme not found. Please check the scheme list."
        )

    return render(
        request,
        "accounts/scheme_details.html",
        {"scheme": scheme},
    )
