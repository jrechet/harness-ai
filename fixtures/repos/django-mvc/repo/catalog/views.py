from django.views.generic import DetailView, ListView

from enrollments.forms import EnrollmentForm

from .models import Course, Session


class SessionListView(ListView):
    """The home page: the sessions still to come, with the seats left on each."""

    template_name = "catalog/session_list.html"
    context_object_name = "sessions"
    paginate_by = 20

    def get_queryset(self):
        sessions = Session.objects.upcoming().with_seats()
        if slug := self.request.GET.get("course"):
            sessions = sessions.filter(course__slug=slug)
        return sessions

    def get_context_data(self, **kwargs):
        slug = self.request.GET.get("course")
        course = Course.objects.filter(slug=slug).first() if slug else None
        return super().get_context_data(course=course, **kwargs)


class SessionDetailView(DetailView):
    template_name = "catalog/session_detail.html"
    context_object_name = "session"
    queryset = Session.objects.with_seats()

    def get_context_data(self, **kwargs):
        return super().get_context_data(form=EnrollmentForm(), **kwargs)
