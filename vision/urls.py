from django.urls import path
from .views import AnalyzeFrameView, ChatCoachView, CreateProfileView, TodayWorkoutView

urlpatterns = [
    path("profile/", CreateProfileView.as_view()),
    path("analyze/", AnalyzeFrameView.as_view()),
    path("workout/today/<int:profile_id>/", TodayWorkoutView.as_view()),
    path("chat/", ChatCoachView.as_view()),

]
