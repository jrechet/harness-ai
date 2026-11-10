from django.urls import path

from . import views

app_name = "enrollments"

urlpatterns = [
    path("sessions/<int:pk>/enroll/", views.enroll, name="enroll"),
    path("sessions/<int:pk>/roster/", views.roster, name="roster"),
    path("enrollments/<int:pk>/cancel/", views.cancel, name="cancel"),
]
