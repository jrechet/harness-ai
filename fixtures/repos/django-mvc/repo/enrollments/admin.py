from django.contrib import admin

from . import services
from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "session", "status", "created_at")
    list_filter = ("status", "session__course")
    list_select_related = ("session__course",)
    search_fields = ("full_name", "email")
    actions = ["cancel_selected"]

    @admin.action(description="Cancel the selected enrollments")
    def cancel_selected(self, request, queryset):
        cancelled = 0
        for enrollment in queryset.exclude(status=Enrollment.Status.CANCELLED):
            services.cancel(enrollment)
            cancelled += 1
        self.message_user(request, f"{cancelled} enrollment(s) cancelled.")
