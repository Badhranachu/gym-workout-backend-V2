from django.urls import path
from .views import create_profile, analyze_frame

urlpatterns = [
    path("profile/", create_profile),
    path("analyze/", analyze_frame),
]
