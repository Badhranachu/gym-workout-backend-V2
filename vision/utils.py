from copy import deepcopy


def calculate_bmi(height_cm, weight):
    h = height_cm / 100
    bmi = weight / (h * h)

    if bmi < 18.5:
        cat = "underweight"
    elif bmi < 25:
        cat = "normal"
    elif bmi < 30:
        cat = "overweight"
    else:
        cat = "obese"

    return round(bmi, 2), cat


WORKOUT_SEQUENCE = ["squat", "pushup"]

WORKOUTS = {
    "underweight": {
        "weight_loss": {
            "pushups": "5x2",
            "squats": "10x2",
        },
        "muscle_gain": {
            "pushups": "8x3",
            "squats": "15x3",
        },
    },
    "normal": {
        "weight_loss": {
            "pushups": "3x1",
            "squats": "3x1",
        },
        "muscle_gain": {
            "pushups": "15x4",
            "squats": "25x4",
        },
    },
    "overweight": {
        "weight_loss": {
            "pushups": "10x4",
            "squats": "25x4",
        },
        "muscle_gain": {
            "pushups": "12x3",
            "squats": "20x3",
        },
    },
    "obese": {
        "weight_loss": {
            "pushups": "6x4",
            "squats": "15x4",
        },
        "muscle_gain": {
            "pushups": "8x3",
            "squats": "12x3",
        },
    },
}


HEALTH_RULES = (
    {
        "keywords": ("knee", "ankle", "leg", "joint", "arthritis"),
        "rep_scale": {"squats": 0.6},
        "set_scale": {"squats": 0.75},
        "tips": (
            "Keep squats shallow and pain-free. Use a chair or wall for support if needed.",
            "Drive up slowly through your heels and stop if knee or ankle pain increases.",
        ),
    },
    {
        "keywords": ("shoulder", "wrist", "elbow", "arm"),
        "rep_scale": {"pushups": 0.6},
        "set_scale": {"pushups": 0.75},
        "tips": (
            "Use incline pushups on a wall, bench, or table to reduce shoulder and wrist stress.",
            "Keep elbows slightly tucked and avoid forcing a painful range of motion.",
        ),
    },
    {
        "keywords": ("back", "spine", "waist", "neck"),
        "rep_scale": {"pushups": 0.75, "squats": 0.75},
        "set_scale": {"pushups": 0.75, "squats": 0.75},
        "tips": (
            "Brace your core and keep your spine neutral during every squat and pushup rep.",
            "Move slower than usual and stop if the movement causes sharp back or neck pain.",
        ),
    },
    {
        "keywords": ("asthma", "breath", "breathing", "heart", "bp", "pressure", "hypertension"),
        "rep_scale": {"pushups": 0.75, "squats": 0.75},
        "set_scale": {"pushups": 0.75, "squats": 0.75},
        "tips": (
            "Work at a comfortable pace, breathe steadily, and rest longer if you feel dizzy or short of breath.",
            "Pause the session and seek medical advice if chest tightness or unusual breathlessness appears.",
        ),
    },
)


def _parse_reps_sets(value):
    reps, sets = value.split("x")
    return int(reps), int(sets)


def _format_reps_sets(reps, sets):
    return f"{max(2, reps)}x{max(1, sets)}"


def _scale_workout(value, rep_scale=1.0, set_scale=1.0):
    reps, sets = _parse_reps_sets(value)
    scaled_reps = max(2, round(reps * rep_scale))
    scaled_sets = max(1, round(sets * set_scale))
    return _format_reps_sets(scaled_reps, scaled_sets)


def _append_unique(items, value):
    if value and value not in items:
        items.append(value)


def build_workout_plan(category, goal, health_issue=""):
    plan = deepcopy(WORKOUTS[category][goal])
    health_issue = str(health_issue or "").strip()
    lowered_issue = health_issue.lower()

    rep_scale = {"pushups": 1.0, "squats": 1.0}
    set_scale = {"pushups": 1.0, "squats": 1.0}
    tips = []

    _append_unique(tips, "Start with squats first, then move to pushups.")
    _append_unique(tips, "Warm up for 5 minutes before the first set and keep every rep controlled.")
    _append_unique(tips, "Keep 5 to 10 seconds of extra pause if your form starts to break.")

    if goal == "muscle_gain":
        _append_unique(tips, "Use a steady tempo and squeeze at the top of each rep for better muscle control.")
    else:
        _append_unique(tips, "Keep your breathing steady and focus on clean reps instead of rushing.")

    matched_rule = False
    for rule in HEALTH_RULES:
        if any(keyword in lowered_issue for keyword in rule["keywords"]):
            matched_rule = True
            for workout_key, scale in rule["rep_scale"].items():
                rep_scale[workout_key] *= scale
            for workout_key, scale in rule["set_scale"].items():
                set_scale[workout_key] *= scale
            for tip in rule["tips"]:
                _append_unique(tips, tip)

    if health_issue and not matched_rule:
        rep_scale["pushups"] *= 0.85
        rep_scale["squats"] *= 0.85
        _append_unique(
            tips,
            "A health issue was noted, so this plan is slightly lighter. Keep every movement pain-free and stop if symptoms increase.",
        )

    plan["pushups"] = _scale_workout(
        plan["pushups"],
        rep_scale=rep_scale["pushups"],
        set_scale=set_scale["pushups"],
    )
    plan["squats"] = _scale_workout(
        plan["squats"],
        rep_scale=rep_scale["squats"],
        set_scale=set_scale["squats"],
    )
    plan["exercise_order"] = WORKOUT_SEQUENCE[:]
    plan["health_issue"] = health_issue
    plan["tips"] = tips
    return plan
