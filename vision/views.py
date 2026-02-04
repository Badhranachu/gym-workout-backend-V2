from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

import base64
import cv2
import numpy as np
import mediapipe as mp

from .models import UserFitnessProfile
from .utils import calculate_bmi, WORKOUTS
from .detect_workout import detect_workout_and_rep,reset_states

mp_pose = mp.solutions.pose



@api_view(["POST"])
@csrf_exempt
def create_profile(request):
    data = request.data

    bmi, category = calculate_bmi(
        float(data["height"]),
        float(data["weight"])
    )

    workout = WORKOUTS[category][data["goal"]]

    profile = UserFitnessProfile.objects.create(
        height=data["height"],
        weight=data["weight"],
        gender=data["gender"],
        goal=data["goal"],
        bmi=bmi,
        bmi_category=category,
        workout_plan=workout
    )

    return Response({
        "profile_id": profile.id,
        "bmi": bmi,
        "category": category,
        "workout": workout
    })


@api_view(['POST'])
@csrf_exempt
def analyze_frame(request):
    image_data = request.data.get("image")
    profile_id = request.data.get("profile_id")

    if not image_data or not profile_id:
        return Response(
            {"error": "image & profile_id required"},
            status=400
        )

    profile = UserFitnessProfile.objects.get(id=profile_id)
    today = timezone.now().date()

    # ✅ FIX: get_or_create (NO CRASH)
    progress, _ = WorkoutProgress.objects.get_or_create(
        profile=profile,
        date=today,
        defaults={
            "program_workout": "pushup",
            "current_set": 1,
            "remaining_reps": int(profile.workout_plan["pushups"].split("x")[0]),
            "total_sets": int(profile.workout_plan["pushups"].split("x")[1]),
        }
    )

    img_bytes = base64.b64decode(image_data.split(",")[1])
    frame = cv2.imdecode(
        np.frombuffer(img_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    ) as pose:

        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # ❌ No person
        if not results.pose_landmarks:
            reset_states()
            return Response({
                "person_detected": False,
                "detected_workout": "none",
                "rep_done": False
            })

        detected_workout, rep_done = detect_workout_and_rep(
            results.pose_landmarks.landmark,
            progress.program_workout
        )

        # 🔥 SAVE ONLY ON REP COMPLETE
        if rep_done:
            progress.remaining_reps -= 1

            if progress.remaining_reps == 0:

                # ---------- NEXT SET ----------
                if progress.current_set < progress.total_sets:
                    progress.current_set += 1
                    reps, _ = profile.workout_plan[
                        progress.program_workout + "s"
                    ].split("x")
                    progress.remaining_reps = int(reps)

                # ---------- NEXT WORKOUT ----------
                else:
                    if progress.program_workout == "pushup":
                        next_workout = "squat"
                    elif progress.program_workout == "squat":
                        next_workout = "situp"
                    else:
                        progress.is_completed = True
                        progress.save()
                        return Response({
                            "completed": True
                        })

                    reps, sets = profile.workout_plan[
                        next_workout + "s"
                    ].split("x")

                    progress.program_workout = next_workout
                    progress.current_set = 1
                    progress.remaining_reps = int(reps)
                    progress.total_sets = int(sets)

            progress.save()

        return Response({
            "person_detected": True,
            "detected_workout": detected_workout,
            "rep_done": rep_done,
            "program_workout": progress.program_workout,
            "current_set": progress.current_set,
            "remaining_reps": progress.remaining_reps,
            "total_sets": progress.total_sets,
            "completed": progress.is_completed
        })

    


from django.utils import timezone
from vision.models import WorkoutProgress
@api_view(["GET"])
def get_today_workout(request, profile_id):
    profile = UserFitnessProfile.objects.get(id=profile_id)
    today = timezone.now().date()

    progress, created = WorkoutProgress.objects.get_or_create(
        profile=profile,
        date=today,
        defaults={
            "program_workout": "pushup",
            "current_set": 1,
            "remaining_reps": int(profile.workout_plan["pushups"].split("x")[0]),
            "total_sets": int(profile.workout_plan["pushups"].split("x")[1]),
        }
    )

    return Response({
        "profile": {
            "height": profile.height,
            "weight": profile.weight,
            "gender": profile.gender,
            "goal": profile.goal,
            "bmi": profile.bmi,
            "category": profile.bmi_category,
        },
        "workout_plan": profile.workout_plan,
        "progress": {
            "program_workout": progress.program_workout,
            "current_set": progress.current_set,
            "remaining_reps": progress.remaining_reps,
            "total_sets": progress.total_sets,
            "completed": progress.is_completed
        }
    })