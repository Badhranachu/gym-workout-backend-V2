from vision.pose import calculate_angle
import time

pushup_stage = "up"
squat_stage = "up"

last_pushup_time = 0
last_squat_time = 0


situp_stage = "down"
last_situp_time = 0
situp_base_shoulder_y = None

REP_COOLDOWN = 1.0

def reset_states():
    global pushup_stage, squat_stage, situp_stage
    global last_pushup_time, last_squat_time, last_situp_time
    global situp_base_shoulder_y

    pushup_stage = "up"
    squat_stage = "up"
    situp_stage = "down"

    last_pushup_time = 0
    last_squat_time = 0
    last_situp_time = 0

    situp_base_shoulder_y = None   # ✅ ADD THIS



def detect_workout_and_rep(landmarks, program_workout):
    global pushup_stage, squat_stage, situp_stage
    global last_pushup_time, last_squat_time, last_situp_time
    global situp_base_shoulder_y

    now = time.time()

    # ==================================================
    # 🔒 PROGRAM PRIORITY MODE (CRITICAL FIX)
    # ==================================================

    # ---------------- PUSHUP ONLY ----------------
    if program_workout == "pushup":
        shoulder = landmarks[11]
        elbow = landmarks[13]
        wrist = landmarks[15]
        hip = landmarks[23]

        pushup_angle = calculate_angle(
            [shoulder.x, shoulder.y],
            [elbow.x, elbow.y],
            [wrist.x, wrist.y]
        )

        body_horizontal = abs(shoulder.y - hip.y) < 0.12
        hip_stable = hip.y > shoulder.y - 0.05

        if body_horizontal and hip_stable:
            detected = "pushup"

            if pushup_angle < 95:
                pushup_stage = "down"

            elif pushup_angle > 160 and pushup_stage == "down":
                if now - last_pushup_time > REP_COOLDOWN:
                    pushup_stage = "up"
                    last_pushup_time = now
                    return "pushup", True

            return detected, False

        return "none", False

    # ---------------- SQUAT ONLY ----------------
    if program_workout == "squat":

        hip = landmarks[23]
        knee = landmarks[25]
        ankle = landmarks[27]

        squat_angle = calculate_angle(
            [hip.x, hip.y],
            [knee.x, knee.y],
            [ankle.x, ankle.y]
        )

        # --- Relaxed thresholds ---
        half_depth = squat_angle < 140      # allow 50% squat
        standing = squat_angle > 160        # relaxed lockout

        # -------- DOWN PHASE --------
        if half_depth:
            squat_stage = "down"
            return "squat", False

        # -------- UP PHASE (REP COMPLETE) --------
        elif standing and squat_stage == "down":
            if now - last_squat_time > REP_COOLDOWN:
                squat_stage = "up"
                last_squat_time = now
                return "squat", True

        return "none", False

    # ---------------- SITUP ONLY ----------------
    if program_workout == "situp":

        shoulder = landmarks[11]
        now = time.time()

        if situp_base_shoulder_y is None:
            situp_base_shoulder_y = shoulder.y

        # Lift amount
        shoulder_lift = situp_base_shoulder_y - shoulder.y

        # ---- Relaxed thresholds ----
        UP_THRESHOLD = 0.06     # reduced from 0.12
        DOWN_THRESHOLD = 0.02   # reduced from 0.05

        # -------- GOING UP --------
        if shoulder_lift > UP_THRESHOLD:
            situp_stage = "up"

        # -------- COMING DOWN → REP COMPLETE --------
        if shoulder_lift < DOWN_THRESHOLD and situp_stage == "up":
            if now - last_situp_time > REP_COOLDOWN:
                situp_stage = "down"
                last_situp_time = now
                return "situp", True

        return "situp", False
