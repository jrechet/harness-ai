from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Session

from . import services
from .forms import EnrollmentForm
from .models import Enrollment


@require_POST
def enroll(request, pk: int):
    session = get_object_or_404(Session.objects.with_seats(), pk=pk)
    form = EnrollmentForm(request.POST)
    if form.is_valid():
        try:
            enrollment = services.enroll(session, **form.cleaned_data)
        except services.AlreadyEnrolled:
            form.add_error("email", "Cette adresse est déjà inscrite à cette session.")
        except services.SessionClosed:
            form.add_error(None, "Les inscriptions à cette session sont closes.")
        else:
            if enrollment.status == Enrollment.Status.CONFIRMED:
                messages.success(request, "Inscription confirmée. Un e-mail de confirmation vous a été envoyé.")
            else:
                messages.info(request, "La session est complète : vous êtes sur liste d'attente.")
            return redirect(session)
    return render(request, "catalog/session_detail.html", {"session": session, "form": form})


@staff_member_required
def roster(request, pk: int):
    session = get_object_or_404(Session.objects.select_related("course"), pk=pk)
    return render(request, "enrollments/roster.html", {"session": session, "enrollments": session.enrollments.all()})


@staff_member_required
@require_POST
def cancel(request, pk: int):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    promoted = services.cancel(enrollment)
    if promoted is not None:
        messages.info(request, f"{promoted.full_name} passe de la liste d'attente aux inscrits.")
    return redirect("enrollments:roster", pk=enrollment.session_id)
