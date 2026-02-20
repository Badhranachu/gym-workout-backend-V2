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


WORKOUTS = {
    "underweight": {
        "weight_loss": {
            "pushups": "5x2",
            "squats": "10x2",
            "situps": "8x2"
        },
        "muscle_gain": {
            "pushups": "8x3",
            "squats": "15x3",
            "situps": "12x3"
        }
    },
    "normal": {
        "weight_loss": {
            "pushups": "3x1",
            "squats": "3x1",
            "situps": "3x1"
        },
        "muscle_gain": {
            "pushups": "15x4",
            "squats": "25x4",
            "situps": "20x4"
        }
    },
    "overweight": {
        "weight_loss": {
            "pushups": "10x4",
            "squats": "25x4",
            "situps": "15x4"
        },
        "muscle_gain": {
            "pushups": "12x3",
            "squats": "20x3",
            "situps": "15x3"
        }
    },
    "obese": {
        "weight_loss": {
            "pushups": "6x4",
            "squats": "15x4",
            "situps": "10x4"
        },
        "muscle_gain": {
            "pushups": "8x3",
            "squats": "12x3",
            "situps": "10x3"
        }
    }
}
