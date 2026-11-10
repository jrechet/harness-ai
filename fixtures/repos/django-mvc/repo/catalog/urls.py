from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.SessionListView.as_view(), name="session_list"),
    path("sessions/<int:pk>/", views.SessionDetailView.as_view(), name="session_detail"),
]
