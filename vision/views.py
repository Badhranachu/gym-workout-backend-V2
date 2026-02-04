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
    program_workout = request.data.get("workout")

    if not image_data or not program_workout:
        return Response({"error": "image & workout required"}, status=400)

    img_bytes = base64.b64decode(image_data.split(",")[1])
    frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    ) as pose:

        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # ❌ No person detected
        if not results.pose_landmarks:
            reset_states()
            return Response({
                "person_detected": False,
                "detected_workout": "none",
                "rep_done": False
            })

        detected_workout, rep_done = detect_workout_and_rep(
            results.pose_landmarks.landmark,
            program_workout
        )

        return Response({
            "person_detected": True,
            "detected_workout": detected_workout,
            "rep_done": rep_done
        })