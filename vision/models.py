from django.db import models

# Create your models here.


from django.db import models

class UserFitnessProfile(models.Model):
    height = models.FloatField()
    weight = models.FloatField()
    gender = models.CharField(max_length=10)
    goal = models.CharField(max_length=30)
    bmi = models.FloatField()
    bmi_category = models.CharField(max_length=20)
    workout_plan = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

from django.utils import timezone

class WorkoutProgress(models.Model):
    profile = models.ForeignKey(UserFitnessProfile, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)

    program_workout = models.CharField(max_length=20, default="pushup")
    current_set = models.IntegerField(default=1)
    remaining_reps = models.IntegerField(default=0)
    total_sets = models.IntegerField(default=0)

    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("profile", "date")