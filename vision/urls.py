from django.urls import path
from .views import create_profile, analyze_frame,get_today_workout

urlpatterns = [
    path("profile/", create_profile),
    path("analyze/", analyze_frame),
    path("workout/today/<int:profile_id>/", get_today_workout),

]
