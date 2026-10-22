
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import SchemeAlert, EligibilityHistory, GovernmentScheme


OFFICIAL_SCHEME_SLUGS = [
    "nsp",
    "pm-kisan",
    "ayushman-bharat",
    "pm-awas",
]


def get_official_schemes():
    return GovernmentScheme.objects.filter(
        slug__in=OFFICIAL_SCHEME_SLUGS
    )


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not all([full_name, username, email, password, confirm_password]):
            messages.error(request, "Please fill in all fields.")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
        elif len(password) < 8:
            messages.error(
                request,
                "Password must contain at least 8 characters."
            )
        else:
            name_parts = full_name.split(maxsplit=1)

            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=name_parts[0],
                last_name=name_parts[1] if len(name_parts) > 1 else "",
            )

            messages.success(
                request,
                "Registration successful. Please log in."
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
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)
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
    user_checks = EligibilityHistory.objects.filter(user=request.user)
    official_schemes = get_official_schemes()

    latest_check = user_checks.order_by("-checked_at").first()
    relevant_categories = ["Healthcare", "Housing"]

    if latest_check:
        occupation = (latest_check.occupation or "").strip().lower()

        if occupation == "student":
            relevant_categories.append("Education")
        elif occupation == "farmer":
            relevant_categories.append("Agriculture")

    recent_alerts = SchemeAlert.objects.filter(
        category__in=relevant_categories
    ).order_by("-created_at")[:3]

    context = {
        "total_users": User.objects.count(),
        "total_schemes": official_schemes.count(),
        "total_checks": EligibilityHistory.objects.count(),
        "total_alerts": 3,
        "my_total_checks": user_checks.count(),
        "recent_checks": user_checks.order_by("-checked_at")[:5],
        "recent_alerts": recent_alerts,
    }

    return render(request, "accounts/home.html", context)


@login_required(login_url="accounts:login")
def check_eligibility(request):
    if request.method != "POST":
        return render(request, "accounts/eligibility.html")

    try:
        age = int(request.POST.get("age", ""))
        income = int(request.POST.get("income", ""))

        if not 0 <= age <= 120 or income < 0:
            raise ValueError

    except (ValueError, TypeError):
        messages.error(
            request,
            "Enter a valid age and annual income."
        )
        return redirect("accounts:eligibility")

    occupation = request.POST.get("occupation", "").strip().lower()
    state = request.POST.get("state", "").strip()
    student_status = request.POST.get("student_status", "").strip().lower()
    farmer_status = request.POST.get("farmer_status", "").strip().lower()
    housing_status = request.POST.get("housing_status", "").strip().lower()

    if not occupation or not state:
        messages.error(
            request,
            "Please select your occupation and state."
        )
        return redirect("accounts:eligibility")

    student = student_status in ("yes", "true", "1")
    farmer = farmer_status in ("yes", "true", "1")
    needs_housing = housing_status in ("yes", "true", "1")

    matching_schemes = []

    for scheme in get_official_schemes():
        eligible = True

        if age < scheme.min_age or age > scheme.max_age:
            eligible = False

        if (
            scheme.max_annual_income is not None
            and income > scheme.max_annual_income
        ):
            eligible = False

        required_occupation = (
            scheme.required_occupation or ""
        ).strip().lower()

        if required_occupation == "student" and not student:
            eligible = False
        elif required_occupation == "farmer" and not farmer:
            eligible = False
        elif required_occupation and required_occupation not in (
            "student",
            "farmer",
        ):
            if occupation != required_occupation:
                eligible = False

        required_state = (
            scheme.required_state or ""
        ).strip().lower()

        if required_state and required_state != state.lower():
            eligible = False

        category = (scheme.category or "").strip().lower()
        name = (scheme.name or "").strip().lower()

        if (
            "education" in category or "scholarship" in name
        ) and not student:
            eligible = False

        if (
            "agriculture" in category
            or "pm-kisan" in name
            or "pm kisan" in name
        ) and not farmer:
            eligible = False

        if (
            getattr(scheme, "requires_land_ownership", False)
            and not farmer
        ):
            eligible = False

        if (
            getattr(scheme, "requires_no_pucca_house", False)
            and not needs_housing
        ):
            eligible = False

        if eligible:
            matching_schemes.append(scheme)

    if matching_schemes:
        result_text = (
            "Potential scheme matches were found. Verify each scheme's "
            "official eligibility requirements before applying."
        )
    else:
        result_text = (
            "No matching schemes were found using the information provided. "
            "Review official scheme requirements for other opportunities."
        )

    history = EligibilityHistory.objects.create(
        user=request.user,
        age=age,
        income=income,
        occupation=occupation,
        result=result_text,
    )

    request.session["eligibility_history_id"] = history.id
    request.session["matching_scheme_ids"] = [
        scheme.id for scheme in matching_schemes
    ]
    request.session["eligibility_result_text"] = result_text

    return redirect("accounts:eligibility_result")


@login_required(login_url="accounts:login")
def eligibility_result(request):
    history_id = request.session.get("eligibility_history_id")

    if not history_id:
        messages.info(
            request,
            "Please complete the eligibility form first."
        )
        return redirect("accounts:eligibility")

    history = get_object_or_404(
        EligibilityHistory,
        id=history_id,
        user=request.user,
    )

    scheme_ids = request.session.get("matching_scheme_ids", [])

    matching_schemes = get_official_schemes().filter(
        id__in=scheme_ids
    )

    context = {
        "history": history,
        "result": request.session.get(
            "eligibility_result_text",
            history.result,
        ),
        "matching_schemes": matching_schemes,
    }

    return render(
        request,
        "accounts/eligibility_result.html",
        context,
    )


@login_required(login_url="accounts:login")
def schemes(request):
    scheme_list = get_official_schemes().order_by("category", "name")

    search_query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    if search_query:
        scheme_list = scheme_list.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__icontains=search_query)
        )

    if category:
        scheme_list = scheme_list.filter(category__iexact=category)

    categories = (
        get_official_schemes()
        .order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )

    return render(
        request,
        "accounts/schemes.html",
        {
            "schemes": scheme_list,
            "categories": categories,
            "search_query": search_query,
            "selected_category": category,
        },
    )


@login_required(login_url="accounts:login")
def live_alerts(request):
    alerts = SchemeAlert.objects.order_by("-created_at")[:3]

    return render(
        request,
        "accounts/alerts.html",
        {
            "alerts": alerts,
            "total_alerts": alerts.count(),
        },
    )


@login_required(login_url="accounts:login")
def user_profile(request):
    user = request.user

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()

        if not full_name or not email:
            messages.error(
                request,
                "Name and email are required."
            )
        elif User.objects.filter(email=email).exclude(pk=user.pk).exists():
            messages.error(request, "That email is already in use.")
        else:
            name_parts = full_name.split(maxsplit=1)

            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ""
            user.email = email
            user.save()

            messages.success(
                request,
                "Profile updated successfully."
            )
            return redirect("accounts:profile")

    return render(
        request,
        "accounts/profile.html",
        {"profile_user": user},
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
    scheme = get_object_or_404(
        get_official_schemes(),
        slug=scheme_name,
    )

    return render(
        request,
        "accounts/scheme_details.html",
        {"scheme": scheme},
    )
