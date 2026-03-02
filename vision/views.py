import base64
import json
import os
from pathlib import Path
from urllib import error as url_error
from urllib import request as url_request

import cv2
import mediapipe as mp
import numpy as np
from django.conf import settings
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from .detect_workout import detect_workout_and_rep, reset_states
from .models import UserFitnessProfile, WorkoutProgress
from .utils import WORKOUTS, calculate_bmi

mp_pose = mp.solutions.pose


def _parse_reps_sets(value):
    reps, sets = value.split("x")
    return int(reps), int(sets)


def _progress_defaults(profile):
    reps, sets = _parse_reps_sets(profile.workout_plan["pushups"])
    return {
        "program_workout": "pushup",
        "current_set": 1,
        "remaining_reps": reps,
        "total_sets": sets,
    }


def _progress_payload(progress):
    return {
        "program_workout": progress.program_workout,
        "current_set": progress.current_set,
        "remaining_reps": progress.remaining_reps,
        "total_sets": progress.total_sets,
        "completed": progress.is_completed,
    }


def _profile_context(profile, progress):
    return (
        f"User profile: height={profile.height}cm, weight={profile.weight}kg, "
        f"gender={profile.gender}, goal={profile.goal}, bmi={profile.bmi}, "
        f"bmi_category={profile.bmi_category}. "
        f"Workout plan={json.dumps(profile.workout_plan)}. "
        f"Today progress: workout={progress.program_workout}, "
        f"set={progress.current_set}/{progress.total_sets}, "
        f"remaining_reps={progress.remaining_reps}, completed={progress.is_completed}."
    )


def _fallback_coach_reply(profile, progress):
    weight = float(profile.weight)
    if profile.goal == "muscle_gain":
        protein_low = round(weight * 1.6, 1)
        protein_high = round(weight * 2.2, 1)
    else:
        protein_low = round(weight * 1.2, 1)
        protein_high = round(weight * 1.8, 1)

    foods = [
        "eggs or paneer/tofu",
        "chicken/fish or lentils/chickpeas",
        "greek yogurt/curd",
        "oats with nuts and seeds",
        "rice + vegetables + lean protein",
    ]

    next_workout = "pushups" if progress.program_workout == "pushup" else "squats"
    hydration = "2.5 to 3.5 liters of water daily"
    return (
        f"Post-workout guidance for your profile:\n"
        f"- BMI: {profile.bmi} ({profile.bmi_category}), goal: {profile.goal}, gender: {profile.gender}\n"
        f"- Protein target: {protein_low}g to {protein_high}g per day\n"
        f"- Food suggestions: {', '.join(foods)}\n"
        f"- Hydration: {hydration}\n"
        f"- Recovery: 7-8 hours sleep, light walk/stretch 10-15 min\n"
        # f"- Next workout focus: {next_workout} (today set {progress.current_set}/{progress.total_sets}, remaining reps {progress.remaining_reps})"
    )


def _read_dotenv_value(key):
    candidates = [
        Path(settings.BASE_DIR) / ".env",
        Path(settings.BASE_DIR).parent / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                env_key, env_val = line.split("=", 1)
                if env_key.strip() == key:
                    return env_val.strip().strip("'").strip('"')
        except OSError:
            continue
    return None


def _get_openrouter_api_key():
    keys = (
        os.getenv("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"),
        os.getenv("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"),
        os.getenv("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"),
        getattr(settings, "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", None),
        _read_dotenv_value("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"),
        _read_dotenv_value("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"),
    )
    for key in keys:
        if key:
            return key
    return None


class CreateProfileView(APIView):
    def post(self, request):
        data = request.data

        required = ("height", "weight", "gender", "goal")
        for field in required:
            if field not in data or data[field] in (None, ""):
                return Response({"error": f"{field} is required"}, status=400)

        try:
            height = float(data["height"])
            weight = float(data["weight"])
        except (TypeError, ValueError):
            return Response({"error": "height and weight must be numeric"}, status=400)

        bmi, category = calculate_bmi(height, weight)
        goal = data["goal"]

        if goal not in WORKOUTS.get(category, {}):
            return Response({"error": "invalid goal"}, status=400)

        workout = WORKOUTS[category][goal]
        profile = UserFitnessProfile.objects.create(
            height=height,
            weight=weight,
            gender=data["gender"],
            goal=goal,
            bmi=bmi,
            bmi_category=category,
            workout_plan=workout,
        )

        return Response(
            {
                "profile_id": profile.id,
                "bmi": bmi,
                "category": category,
                "workout": workout,
            }
        )


class AnalyzeFrameView(APIView):
    def post(self, request):
        image_data = request.data.get("image")
        profile_id = request.data.get("profile_id")

        if not image_data or not profile_id:
            return Response({"error": "image and profile_id are required"}, status=400)

        try:
            profile = UserFitnessProfile.objects.get(id=profile_id)
        except UserFitnessProfile.DoesNotExist:
            return Response({"error": "profile not found"}, status=404)

        today = timezone.now().date()
        progress, _ = WorkoutProgress.objects.get_or_create(
            profile=profile,
            date=today,
            defaults=_progress_defaults(profile),
        )

        if progress.is_completed:
            return Response({"completed": True, **_progress_payload(progress)})

        try:
            encoded = image_data.split(",", 1)[1]
            img_bytes = base64.b64decode(encoded)
        except (IndexError, ValueError, TypeError):
            return Response({"error": "invalid image format"}, status=400)

        frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return Response({"error": "could not decode image"}, status=400)

        with mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        ) as pose:
            results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        if not results.pose_landmarks:
            reset_states()
            return Response(
                {
                    "person_detected": False,
                    "detected_workout": "none",
                    "rep_done": False,
                    **_progress_payload(progress),
                }
            )

        detected_workout, rep_done = detect_workout_and_rep(
            results.pose_landmarks.landmark,
            progress.program_workout,
        )

        if rep_done:
            progress.remaining_reps -= 1

            if progress.remaining_reps == 0:
                if progress.current_set < progress.total_sets:
                    progress.current_set += 1
                    reps, _ = _parse_reps_sets(
                        profile.workout_plan[progress.program_workout + "s"]
                    )
                    progress.remaining_reps = reps
                else:
                    if progress.program_workout == "pushup":
                        next_workout = "squat"
                    else:
                        progress.is_completed = True
                        progress.save()
                        return Response({"completed": True, **_progress_payload(progress)})

                    reps, sets = _parse_reps_sets(profile.workout_plan[next_workout + "s"])
                    progress.program_workout = next_workout
                    progress.current_set = 1
                    progress.remaining_reps = reps
                    progress.total_sets = sets

            progress.save()

        return Response(
            {
                "person_detected": True,
                "detected_workout": detected_workout,
                "rep_done": rep_done,
                **_progress_payload(progress),
            }
        )


class TodayWorkoutView(APIView):
    def get(self, request, profile_id):
        try:
            profile = UserFitnessProfile.objects.get(id=profile_id)
        except UserFitnessProfile.DoesNotExist:
            return Response({"error": "profile not found"}, status=404)

        today = timezone.now().date()
        progress, _ = WorkoutProgress.objects.get_or_create(
            profile=profile,
            date=today,
            defaults=_progress_defaults(profile),
        )

        return Response(
            {
                "profile": {
                    "height": profile.height,
                    "weight": profile.weight,
                    "gender": profile.gender,
                    "goal": profile.goal,
                    "bmi": profile.bmi,
                    "category": profile.bmi_category,
                },
                "workout_plan": profile.workout_plan,
                "progress": _progress_payload(progress),
            }
        )


class ChatCoachView(APIView):
    def post(self, request):
        message = (request.data.get("message") or "").strip()
        profile_id = request.data.get("profile_id")
        history = request.data.get("history") or []

        if not message:
            return Response({"error": "message is required"}, status=400)
        if not profile_id:
            return Response({"error": "profile_id is required"}, status=400)

        try:
            profile = UserFitnessProfile.objects.get(id=profile_id)
        except UserFitnessProfile.DoesNotExist:
            return Response({"error": "profile not found"}, status=404)

        today = timezone.now().date()
        progress, _ = WorkoutProgress.objects.get_or_create(
            profile=profile,
            date=today,
            defaults=_progress_defaults(profile),
        )

        api_key = _get_openrouter_api_key()
        if not api_key:
            return Response(
                {
                    "reply": _fallback_coach_reply(profile, progress),
                    "source": "local_fallback",
                    "warning": "OPENROUTER_API_KEY is missing. Configure key to use OpenRouter responses.",
                }
            )

        cleaned_history = []
        if isinstance(history, list):
            for item in history[-8:]:
                if not isinstance(item, dict):
                    continue
                role = item.get("role")
                content = (item.get("content") or "").strip()
                if role in ("user", "assistant") and content:
                    cleaned_history.append({"role": role, "content": content[:1200]})

        system_prompt = (
            "You are a gym coach assistant. Give short, practical guidance about "
            "post-workout recovery, food, protein intake, next exercises, and safe form. "
            "Keep responses concise and clear. "
            + _profile_context(profile, progress)
        )

        payload = {
            "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": system_prompt},
                *cleaned_history,
                {"role": "user", "content": message},
            ],
            "temperature": 0.4,
            "max_tokens": 320,
        }

        req = url_request.Request(
            url="https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:5173"),
                "X-Title": "Gym AI Coach",
            },
            method="POST",
        )

        try:
            with url_request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except url_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return Response(
                {
                    "reply": _fallback_coach_reply(profile, progress),
                    "source": "local_fallback",
                    "warning": "OpenRouter HTTP error",
                    "detail": detail,
                }
            )
        except Exception as exc:
            return Response(
                {
                    "reply": _fallback_coach_reply(profile, progress),
                    "source": "local_fallback",
                    "warning": "OpenRouter request failed",
                    "detail": str(exc),
                }
            )

        try:
            reply = body["choices"][0]["message"]["content"].strip()
        except Exception:
            return Response(
                {
                    "reply": _fallback_coach_reply(profile, progress),
                    "source": "local_fallback",
                    "warning": "Invalid OpenRouter response payload",
                }
            )

        return Response({"reply": reply})
