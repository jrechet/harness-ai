from django.contrib import admin

from .models import Course, Session


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("course", "starts_at", "location", "capacity")
    list_filter = ("course",)
    date_hierarchy = "starts_at"
