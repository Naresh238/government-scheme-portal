import uuid
from functools import wraps
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from .models import (
    Citizen,
    Application,
    ApplicationDocument,
    Document,
    PortalQueryMessage,
    Department,
)

User = get_user_model()


# ==================================================
# GET CITIZEN PROFILE
# ==================================================

def get_citizen(request):
    citizen, created = Citizen.objects.get_or_create(
        user=request.user,
        defaults={
            "name": (
                request.user.get_full_name()
                or request.user.username
            ),
            "email": request.user.email or "",
            "mobile_number": "",
        },
    )

    if not citizen.email and request.user.email:
        citizen.email = request.user.email
        citizen.save(update_fields=["email"])

    return citizen


# ==================================================
# CITIZEN LOGIN AND ROLE CHECK
# ==================================================

def citizen_required(view_func):

    @wraps(view_func)
    @login_required(login_url="accounts:login")
    def wrapper(request, *args, **kwargs):

        user = request.user

        is_department = user.groups.filter(
            name="Department"
        ).exists()

        is_admin = (
            user.is_staff
            or user.is_superuser
            or user.groups.filter(name="Admin").exists()
        )

        is_citizen = Citizen.objects.filter(
            user=user
        ).exists()

        if (
            not user.is_active
            or is_department
            or is_admin
            or not is_citizen
        ):
            messages.error(
                request,
                "This page is available only to citizen accounts."
            )
            return redirect("accounts:home")

        return view_func(request, *args, **kwargs)

    return wrapper


# ==================================================
# CITIZEN CONVERSATIONS
# ==================================================

def citizen_conversations(citizen):

    return PortalQueryMessage.objects.filter(
        Q(
            sender_type="Citizen",
            sender_id=citizen.pk,
        )
        |
        Q(
            receiver_type="Citizen",
            receiver_id=citizen.pk,
        )
    ).order_by("posted_date", "id")


# ==================================================
# CITIZEN DASHBOARD
# ==================================================

@citizen_required
def dashboard(request):

    citizen = get_citizen(request)

    applications_list = (
        Application.objects.filter(citizen=citizen)
        .select_related("scheme")
        .prefetch_related(
            "uploaded_documents",
            "scheme__required_documents",
        )
        .order_by("-applied_date")
    )

    all_documents = ApplicationDocument.objects.filter(
        application__citizen=citizen
    )

    # Collect required documents only for this citizen's applications.
    required_documents_by_scheme = []

    for application in applications_list:
        required_documents_by_scheme.append({
            "application": application,
            "scheme": application.scheme,
            "documents": application.scheme.required_documents.all(),
        })

    all_messages = citizen_conversations(citizen)

    context = {
        "citizen": citizen,

        "applications": applications_list[:5],
        "required_documents_by_scheme": required_documents_by_scheme,
        "total_applications": applications_list.count(),

        "pending_applications": applications_list.filter(
            application_status__in=[
                "submitted",
                "under_review",
                "documents_required",
            ]
        ).count(),

        "approved_applications": applications_list.filter(
            application_status="approved"
        ).count(),

        "rejected_applications": applications_list.filter(
            application_status="rejected"
        ).count(),

        "total_documents": all_documents.count(),

        "pending_documents": all_documents.filter(
            verification_status="pending"
        ).count(),

        "verified_documents": all_documents.filter(
            verification_status="verified"
        ).count(),

        "rejected_documents": all_documents.filter(
            verification_status="rejected"
        ).count(),

        "total_queries": all_messages.values(
            "conversation_id"
        ).distinct().count(),

        "recent_queries": all_messages.order_by(
            "-posted_date",
            "-id",
        )[:5],
    }

    return render(
        request,
        "accounts/citizen_dashboard.html",
        context,
    )


# ==================================================
# VIEW APPLICATIONS AND UPLOAD DOCUMENTS
# ==================================================

@citizen_required
def applications(request):

    citizen = get_citizen(request)

    application_list = (
        Application.objects.filter(citizen=citizen)
        .select_related("scheme")
        .prefetch_related(
            "uploaded_documents",
            "scheme__required_documents",
        )
        .order_by("-applied_date")
    )

    if request.method == "POST":

        application_id = request.POST.get("application_id")
        document_id = request.POST.get("document_id")
        uploaded_file = request.FILES.get("document_file")

        if not application_id or not document_id:
            messages.error(
                request,
                "Invalid application or document."
            )
            return redirect("accounts:citizen_applications")

        if not uploaded_file:
            messages.error(
                request,
                "Please select a document file."
            )
            return redirect("accounts:citizen_applications")

        application = get_object_or_404(
            Application,
            pk=application_id,
            citizen=citizen,
        )

        document = get_object_or_404(
            Document,
            pk=document_id,
            scheme=application.scheme,
        )

        allowed_extensions = {
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
        }

        extension = Path(uploaded_file.name).suffix.lower()

        if extension not in allowed_extensions:
            messages.error(
                request,
                "Only PDF, JPG, JPEG and PNG files are allowed."
            )
            return redirect("accounts:citizen_applications")

        if uploaded_file.size > 5 * 1024 * 1024:
            messages.error(
                request,
                "File size must not exceed 5 MB."
            )
            return redirect("accounts:citizen_applications")

        if uploaded_file.size == 0:
            messages.error(
                request,
                "The uploaded file is empty."
            )
            return redirect("accounts:citizen_applications")

        existing = ApplicationDocument.objects.filter(
            application=application,
            document=document,
        ).first()

        try:
            with transaction.atomic():

                if existing:

                    existing.file_path = uploaded_file
                    existing.verification_status = "pending"
                    existing.remarks = ""
                    existing.save()

                else:

                    ApplicationDocument.objects.create(
                        application=application,
                        document=document,
                        file_path=uploaded_file,
                        verification_status="pending",
                    )

        except Exception:
            messages.error(
                request,
                "Document upload failed. Please try again."
            )
            return redirect("accounts:citizen_applications")

        messages.success(
            request,
            "Document uploaded successfully."
        )

        return redirect("accounts:citizen_applications")

    return render(
        request,
        "accounts/citizen_applications.html",
        {
            "applications": application_list,
        },
    )


# ==================================================
# FIND ACTIVE ADMIN USER
# ==================================================

def get_active_admin():

    admin_user = User.objects.filter(
        is_active=True,
        groups__name="Admin",
    ).order_by("id").first()

    if admin_user:
        return admin_user

    admin_user = User.objects.filter(
        is_active=True,
        is_superuser=True,
    ).order_by("id").first()

    if admin_user:
        return admin_user

    return User.objects.filter(
        is_active=True,
        is_staff=True,
    ).order_by("id").first()


# ==================================================
# FIND DEPARTMENT USER
# ==================================================

def get_department_user(department):

    return User.objects.filter(
        email__iexact=department.email,
        is_active=True,
        groups__name="Department",
    ).order_by("id").first()


# ==================================================
# CREATE A NEW CITIZEN QUERY
# ==================================================

def create_citizen_query(
    citizen,
    subject,
    message_text,
    recipient_type,
    department_id=None,
):

    if recipient_type == "Admin":

        admin_user = get_active_admin()

        if admin_user is None:
            return False, "No active Admin account is available."

        receiver_id = admin_user.pk

    elif recipient_type == "Department":

        if not department_id:
            return False, "Please select a Department."

        department = get_object_or_404(
            Department,
            pk=department_id,
            status="Active",
        )

        department_user = get_department_user(department)

        if department_user is None:
            return False, "No active user is linked to this Department."

        receiver_id = department_user.pk

    else:

        return False, "Please select Admin or Department."

    PortalQueryMessage.objects.create(
        conversation_id=uuid.uuid4(),
        sender_id=citizen.pk,
        sender_type="Citizen",
        receiver_id=receiver_id,
        receiver_type=recipient_type,
        subject=subject,
        message=message_text,
        status="Open",
    )

    return True, "Your query was submitted successfully."


# ==================================================
# VALIDATE QUERY RECIPIENT
# ==================================================

def validate_query_recipient(receiver_id, receiver_type):

    if receiver_type == "Admin":

        return User.objects.filter(
            pk=receiver_id,
            is_active=True,
        ).filter(
            Q(groups__name="Admin")
            | Q(is_staff=True)
            | Q(is_superuser=True)
        ).exists()

    if receiver_type == "Department":

        department_user = User.objects.filter(
            pk=receiver_id,
            is_active=True,
            groups__name="Department",
        ).first()

        if department_user is None:
            return False

        return Department.objects.filter(
            email__iexact=department_user.email,
            status="Active",
        ).exists()

    return False


# ==================================================
# CITIZEN QUERIES, REPLIES AND HISTORY
# ==================================================

@citizen_required
def queries(request):

    citizen = get_citizen(request)

    if request.method == "POST":

        action = request.POST.get("action", "new")

        message_text = request.POST.get(
            "message",
            "",
        ).strip()

        if not message_text:
            messages.error(
                request,
                "Please enter your message."
            )
            return redirect("accounts:citizen_queries")

        # ==========================================
        # CREATE NEW QUERY
        # ==========================================

        if action == "new":

            subject = request.POST.get(
                "subject",
                "",
            ).strip()

            recipient_type = request.POST.get(
                "recipient_type",
                "",
            ).strip()

            department_id = request.POST.get(
                "department_id"
            )

            if not subject:
                messages.error(
                    request,
                    "Please enter a subject."
                )
                return redirect("accounts:citizen_queries")

            success, result = create_citizen_query(
                citizen=citizen,
                subject=subject,
                message_text=message_text,
                recipient_type=recipient_type,
                department_id=department_id,
            )

            if success:
                messages.success(request, result)
            else:
                messages.error(request, result)

            return redirect("accounts:citizen_queries")

        # ==========================================
        # REPLY TO EXISTING QUERY
        # ==========================================

        elif action == "reply":

            conversation_id = request.POST.get(
                "conversation_id",
                "",
            )

            try:
                conversation_id = uuid.UUID(
                    conversation_id
                )

            except (
                ValueError,
                TypeError,
                AttributeError,
            ):
                messages.error(
                    request,
                    "Invalid conversation."
                )
                return redirect("accounts:citizen_queries")

            conversation = citizen_conversations(
                citizen
            ).filter(
                conversation_id=conversation_id
            )

            first_message = conversation.order_by(
                "posted_date",
                "id",
            ).first()

            last_message = conversation.order_by(
                "-posted_date",
                "-id",
            ).first()

            if first_message is None or last_message is None:
                messages.error(
                    request,
                    "Conversation not found."
                )
                return redirect("accounts:citizen_queries")

            # Determine the other participant.
            if last_message.sender_type == "Citizen":

                receiver_id = last_message.receiver_id
                receiver_type = last_message.receiver_type

            elif last_message.receiver_type == "Citizen":

                receiver_id = last_message.sender_id
                receiver_type = last_message.sender_type

            else:

                messages.error(
                    request,
                    "Invalid conversation participants."
                )
                return redirect("accounts:citizen_queries")

            if receiver_type not in ("Admin", "Department"):
                messages.error(
                    request,
                    "This conversation cannot be replied to."
                )
                return redirect("accounts:citizen_queries")

            if not validate_query_recipient(
                receiver_id,
                receiver_type,
            ):
                messages.error(
                    request,
                    "The recipient account is no longer active."
                )
                return redirect("accounts:citizen_queries")

            with transaction.atomic():

                PortalQueryMessage.objects.create(
                    conversation_id=conversation_id,
                    sender_id=citizen.pk,
                    sender_type="Citizen",
                    receiver_id=receiver_id,
                    receiver_type=receiver_type,
                    subject=first_message.subject,
                    message=message_text,
                    status="Open",
                    parent_message=last_message,
                )

            messages.success(
                request,
                "Your reply was submitted successfully."
            )

            return redirect("accounts:citizen_queries")

        else:

            messages.error(
                request,
                "Invalid query action."
            )
            return redirect("accounts:citizen_queries")

    # ==============================================
    # DISPLAY COMPLETE CONVERSATION HISTORY
    # ==============================================

    all_messages = citizen_conversations(citizen)

    grouped = {}

    for item in all_messages:

        key = str(item.conversation_id)

        if key not in grouped:

            grouped[key] = {
                "conversation_id": item.conversation_id,
                "subject": item.subject,
                "status": item.status,
                "messages": [],
                "latest_date": item.posted_date,
            }

        grouped[key]["messages"].append(item)

        if item.posted_date >= grouped[key]["latest_date"]:
            grouped[key]["latest_date"] = item.posted_date
            grouped[key]["status"] = item.status

    conversations = sorted(
        grouped.values(),
        key=lambda item: item["latest_date"],
        reverse=True,
    )

    departments = Department.objects.filter(
        status="Active"
    ).order_by("department_name")

    return render(
        request,
        "accounts/citizen_queries.html",
        {
            "citizen": citizen,
            "conversations": conversations,
            "departments": departments,
        },
    )