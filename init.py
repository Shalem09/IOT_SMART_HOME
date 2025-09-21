# init.py  — Proofing config (בקרת התפחת בצק)

import os
import socket

# 0 = שרת פנימי, 1 = HiveMQ public
nb = 1
brokers = [
    str(socket.gethostbyname("vmm1.saaintertrade.com")),
    str(socket.gethostbyname("broker.hivemq.com")),
    "18.194.176.210",  # תוקן רווח שגוי ב-IP
]
ports = [80, 1883, 1883]
usernames = ["", "", ""]
passwords = ["", "", ""]

broker_ip   = brokers[nb]
broker_port = int(ports[nb])  # חשוב: מספר (int)
username    = usernames[nb]
password    = passwords[nb]

# זמן חיבור (0 = ללא הגבלת זמן)
conn_time = 0
wait_time = 5

# ===== נושאי MQTT (Topics) =====
# בסיס לכל הנושאים במערכת ההתפחה (שמור "/" בסוף!)
comm_topic = "pr/Proofing/BakeryA/"

# ---- אמולטורים/חיישנים ישדרו ל:
# AirEnv         -> pr/Proofing/BakeryA/env-1/pub
# DoughMoisture  -> pr/Proofing/BakeryA/doughH-1/pub
# DoughRise      -> pr/Proofing/BakeryA/rise-1/pub
# ProofTimer     -> pr/Proofing/BakeryA/timer-1/pub
# התראות מנהל   -> pr/Proofing/BakeryA/alarm   (ללא /pub)

# ===== פרופיל התפחה (ספי אזהרה/יעדים) =====
PROOF_TEMP_MIN   = 27.0   # °C
PROOF_TEMP_MAX   = 32.0
PROOF_HUM_MIN    = 70.0   # %RH
PROOF_HUM_MAX    = 85.0
DOUGH_MOIST_MIN  = 55.0   # % לחות בבצק (חיישן קיבולי/מודל)
DOUGH_MOIST_MAX  = 65.0
RISE_TARGET_PCT  = 75.0   # יעד תפיחה באחוזים
ALERT_COOLDOWN   = 60     # שניות בין התראות מאותו סוג

# ===== כללי (אם לא משתמשים – להשאיר) =====
isplot = False
issave = False
percen_thr = 0.05
Fs = 2048.0
deviation_percentage = 10
max_eucl = 0.5

# ===== מרווחי עבודה =====
acqtime   = 60.0  # sec
manag_time = 10   # sec

# ===== מסד נתונים =====
BASE_DIR = os.path.dirname(__file__)
db_name  = os.path.join(BASE_DIR, "data", "DreamGuard.db")
# אתחול סכימה וזרעים (להריץ פעם אחת כשמשנים את סוגי המכשירים)
db_init  = False   # הפוך ל-True → הרץ data_acq.py → החזר ל-False

# ===== שאריות מהמערכת הישנה (לא בשימוש בפרופינג) =====
# נשארים כאן כדי לא לשבור קוד ישן אם הוא עוד קורא להם.
sensitivityMax = 0.02
Elec_max       = 1.8
