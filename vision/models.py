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
