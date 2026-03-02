import time

from vision.pose import calculate_angle

pushup_stage = "up"
squat_stage = "up"

last_pushup_time = 0
last_squat_time = 0

REP_COOLDOWN = 1.0


def reset_states():
    global pushup_stage, squat_stage
    global last_pushup_time, last_squat_time

    pushup_stage = "up"
    squat_stage = "up"

    last_pushup_time = 0
    last_squat_time = 0


def detect_workout_and_rep(landmarks, program_workout):
    global pushup_stage, squat_stage
    global last_pushup_time, last_squat_time

    now = time.time()

    if program_workout == "pushup":
        shoulder = landmarks[11]
        elbow = landmarks[13]
        wrist = landmarks[15]
        hip = landmarks[23]

        pushup_angle = calculate_angle(
            [shoulder.x, shoulder.y],
            [elbow.x, elbow.y],
            [wrist.x, wrist.y],
        )

        body_horizontal = abs(shoulder.y - hip.y) < 0.12
        hip_stable = hip.y > shoulder.y - 0.05

        if body_horizontal and hip_stable:
            if pushup_angle < 95:
                pushup_stage = "down"
            elif pushup_angle > 160 and pushup_stage == "down":
                if now - last_pushup_time > REP_COOLDOWN:
                    pushup_stage = "up"
                    last_pushup_time = now
                    return "pushup", True

            return "pushup", False

        return "none", False

    if program_workout == "squat":
        hip = landmarks[23]
        knee = landmarks[25]
        ankle = landmarks[27]

        squat_angle = calculate_angle(
            [hip.x, hip.y],
            [knee.x, knee.y],
            [ankle.x, ankle.y],
        )

        half_depth = squat_angle < 140
        standing = squat_angle > 160

        if half_depth:
            squat_stage = "down"
            return "squat", False
        if standing and squat_stage == "down":
            if now - last_squat_time > REP_COOLDOWN:
                squat_stage = "up"
                last_squat_time = now
                return "squat", True

        return "none", False

    return "none", False
