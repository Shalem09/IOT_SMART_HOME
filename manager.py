# Manager for Proofing System (Bakery) – DB writer + alarm logic

import re
import time
import random
from datetime import datetime

import paho.mqtt.client as mqtt
from icecream import ic

from init import *           # comm_topic, broker_ip, broker_port, db_name, manag_time, etc.
import data_acq as da        # add_IOT_data, fetch_data, timestamp, check_changes, update_IOT_status

def time_format():
    return f'{datetime.now()}  Manager|> '

ic.configureOutput(prefix=time_format)
ic.configureOutput(includeContext=False)

# ====== קונפיגורציה למניעת "קפיצות" ALARM בדשבורד ======
# לא לפרסם הודעות ALARM לדשבורד (אפשר להדליק בעתיד אם תרצה)
SEND_EXTERNAL_ALARMS = False
# אם תחליט לפרסם, האם לשמור retained (מומלץ False כדי שלא יישארו "מהבית")
ALARM_RETAIN = False

# בסיס נושאים עקבי (גם אם comm_topic לא מסתיים ב־"/")
TOPIC_BASE = comm_topic.rstrip('/')
ALARM_TOPIC = f"{TOPIC_BASE}/alarm"

# ------------------ ספי התפחה (ניתן להתאים לפי הצורך) ------------------
AIR_TEMP_RANGE     = (27.0, 32.0)    # °C טמפ' אוויר בחלון ההתפחה
AIR_HUM_RANGE      = (70.0, 85.0)    # % לחות יחסית באוויר
DOUGH_MOIST_RANGE  = (60.0, 75.0)    # % לחות/מוליכות בבצק (מד סימבולי)
HYDRATION_RANGE    = (0.55, 0.80)    # יחס מים/קמח
VOLUME_TARGET_MIN  = 1.80            # פי כמה מנפח התחלתי (מדד יחסי)
PROOF_MAX_HOURS    = 3.0             # ש׳ מקסימום להתפחה
OVEN_READY_TEMP    = 180.0           # °C תנור מוכן

# ------------------ Callbacks ------------------
def on_log(client, userdata, level, buf):
    ic("log: " + buf)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        ic("connected OK")
    else:
        ic("Bad connection Returned code=", rc)

def on_disconnect(client, userdata, rc, properties=None):
    ic("DisConnected result code " + str(rc))

def on_message(client, userdata, msg):
    topic = msg.topic
    m_decode = str(msg.payload.decode("utf-8", "ignore"))
    ic("message from: " + topic, m_decode)
    insert_and_evaluate(client, topic, m_decode)

# ------------------ MQTT init ------------------
def client_init(cname):
    r = random.randrange(1, 10000000)
    ID = str(cname + str(r + 21))

    # MQTT v3.1.1 עם clean_session; תואם גם ל-Broker פתוחים
    client = mqtt.Client(
        client_id=ID,
        clean_session=True,
        protocol=mqtt.MQTTv311,
        transport="tcp"
        # אם תרצה לעבור ל-Callback API V2:
        # , callback_api_version=mqtt.CallbackAPIVersion.V2
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_log = on_log
    client.on_message = on_message
    if username != "":
        client.username_pw_set(username, password)
    ic("Connecting to broker ", broker_ip)
    client.connect(broker_ip, int(broker_port))  # connect to broker
    return client

# ------------------ עזרי פרסום ------------------
def enable(client, topic, msg, retain=False):
    ic(topic + ' ' + msg)
    client.publish(topic, msg, qos=0, retain=retain)

def alarm(client, msg):
    # לוג תמיד — כדי שתראה מה *היה* נשלח
    ic(f"ALARM -> {ALARM_TOPIC}: {msg}")
    # פרסום בפועל רק אם הדגל דלוק
    if SEND_EXTERNAL_ALARMS:
        enable(client, ALARM_TOPIC, msg, retain=ALARM_RETAIN)

# ------------------ פירוק הודעות + כתיבה ל-DB + בדיקת ספים ------------------
_num = r'([-+]?\d+(?:\.\d+)?)'  # מספר עשרוני/שלם

def insert_and_evaluate(client, topic, payload):
    """
    מזהה את סוג ההודעה לפי ה־topic/תוכן, כותב ל־DB ומתריע אם ערכים מחוץ לספים.
    מאפשר גם תאימות לאחור (DHT / ElecMeter).
    """

    wrote_something = False

    # --- AirEnv: "From: AirEnv Temperature: <num> Humidity: <num>"
    if topic.endswith('/env-1/pub') or 'AirEnv' in payload:
        mt = re.search(r'Temperature:\s*' + _num, payload)
        mh = re.search(r'Humidity:\s*'    + _num, payload)
        if mt:
            t = float(mt.group(1))
            da.add_IOT_data('AirEnv_Temperature', da.timestamp(), t); wrote_something = True
            if not (AIR_TEMP_RANGE[0] <= t <= AIR_TEMP_RANGE[1]):
                alarm(client, f"Air temperature out of range: {t:.1f}°C (target {AIR_TEMP_RANGE[0]}–{AIR_TEMP_RANGE[1]}°C)")
        if mh:
            h = float(mh.group(1))
            da.add_IOT_data('AirEnv_Humidity', da.timestamp(), h); wrote_something = True
            if not (AIR_HUM_RANGE[0] <= h <= AIR_HUM_RANGE[1]):
                alarm(client, f"Air humidity out of range: {h:.0f}% (target {AIR_HUM_RANGE[0]}–{AIR_HUM_RANGE[1]}%)")
        if wrote_something:
            return

    # --- DoughMoisture: "From: DoughMoisture Moisture: <num%> Hydration: <num>"
    if topic.endswith('/dough-1/pub') or 'DoughMoisture' in payload or 'Moisture:' in payload:
        mm = re.search(r'Moisture:\s*'   + _num, payload)
        mh = re.search(r'Hydration:\s*'  + _num, payload)
        if mm:
            m = float(mm.group(1))
            da.add_IOT_data('DoughMoisture', da.timestamp(), m); wrote_something = True
            if not (DOUGH_MOIST_RANGE[0] <= m <= DOUGH_MOIST_RANGE[1]):
                alarm(client, f"Dough moisture out of range: {m:.0f}% (target {DOUGH_MOIST_RANGE[0]}–{DOUGH_MOIST_RANGE[1]}%)")
        if mh:
            hy = float(mh.group(1))
            da.add_IOT_data('Hydration', da.timestamp(), hy); wrote_something = True
            if not (HYDRATION_RANGE[0] <= hy <= HYDRATION_RANGE[1]):
                alarm(client, f"Hydration ratio out of range: {hy:.2f} (target {HYDRATION_RANGE[0]}–{HYDRATION_RANGE[1]})")
        if wrote_something:
            return

    # --- VolumeSensor: "From: VolumeSensor Volume: <num>"
    if topic.endswith('/vol-1/pub') or 'VolumeSensor' in payload or 'Volume:' in payload:
        mv = re.search(r'Volume:\s*' + _num, payload)
        if mv:
            v = float(mv.group(1))
            da.add_IOT_data('DoughVolume', da.timestamp(), v); wrote_something = True
            if v >= VOLUME_TARGET_MIN:
                alarm(client, f"Dough has proofed enough (volume ×{v:.2f} ≥ {VOLUME_TARGET_MIN}).")
        if wrote_something:
            return

    # --- Timer/Oven:
    # דוגמאות נתמכות:
    # "From: Timer Remaining: 120 min"  | "Timer: 1:30:00" | "Timer: Done"
    # "From: Oven OvenTemp: 185"        | "Oven: 185"
    if topic.endswith('/timer-1/pub') or 'Timer' in payload:
        if re.search(r'Done|Finish|End', payload, re.I):
            alarm(client, "Proofing time completed. Proceed to baking.")
            return
        # H:MM:SS
        m_hms = re.search(r'(\d+):(\d{2}):(\d{2})', payload)
        if m_hms:
            hours = int(m_hms.group(1)) + int(m_hms.group(2))/60 + int(m_hms.group(3))/3600
            da.add_IOT_data('TimerHours', da.timestamp(), hours); wrote_something = True
            if hours > PROOF_MAX_HOURS:
                alarm(client, f"Proofing time exceeded {hours:.2f} h (> {PROOF_MAX_HOURS} h).")
            return
        # Remaining/Elapsed with units
        m_num_unit = re.search(_num + r'\s*(h|hr|hrs|hour|hours|min|m|minutes?)', payload, re.I)
        if m_num_unit:
            val = float(m_num_unit.group(1))
            unit = m_num_unit.group(2).lower()
            hours = val if unit.startswith('h') else (val / 60.0)
            da.add_IOT_data('TimerHours', da.timestamp(), hours); wrote_something = True
            if hours > PROOF_MAX_HOURS:
                alarm(client, f"Proofing time exceeded {hours:.2f} h (> {PROOF_MAX_HOURS} h).")
            return

    if topic.endswith('/oven-1/pub') or 'Oven' in payload:
        mo = re.search(r'(OvenTemp|Temp):\s*' + _num, payload, re.I)
        if mo:
            # ההחזרה של re כאן נותנת מספר בקבוצה האחרונה — ניקח אותה באופן כללי:
            val = mo.groups()[-1]
            t = float(val)
            da.add_IOT_data('OvenTemp', da.timestamp(), t); wrote_something = True
            if t >= OVEN_READY_TEMP:
                alarm(client, f"Oven reached target temperature: {t:.0f}°C (≥ {OVEN_READY_TEMP:.0f}°C).")
            return

    # === תאימות לאחור (אם נשארו אמולטורים ישנים) ===

    # DHT case: 'From: DHT-1 Temperature: 25 Humidity: 40'
    if 'DHT' in payload and ' Temperature: ' in payload:
        try:
            value = payload.split(' Temperature: ')[1].split(' Humidity: ')[0]
            dev = payload.split('From: ')[1].split(' Temperature: ')[0]
            da.add_IOT_data(dev, da.timestamp(), value)
            return
        except Exception:
            pass

    # Elec Meter case: '... Electricity: <num> Sensitivity: <num>'
    if 'Meter' in payload and ' Electricity: ' in payload and ' Sensitivity: ' in payload:
        elec = payload.split(' Electricity: ')[1].split(' Sensitivity: ')[0]
        sens = payload.split(' Sensitivity: ')[1]
        da.add_IOT_data('ElectricityMeter', da.timestamp(), elec)
        da.add_IOT_data('SensitivityMeter', da.timestamp(), sens)
        return

# ------------------ בדיקות מחזוריות מול ה-DB ------------------
def _last_float(table_name, dev_name):
    df = da.fetch_data(db_name, table_name, dev_name)
    if df is None or len(df) == 0:
        return None
    try:
        return float(df['value'].iloc[-1])
    except Exception:
        return None

def check_DB_for_change(client):
    # AirEnv
    t = _last_float('data', 'AirEnv_Temperature')
    if t is not None and not (AIR_TEMP_RANGE[0] <= t <= AIR_TEMP_RANGE[1]):
        alarm(client, f"Air temperature out of range: {t:.1f}°C (target {AIR_TEMP_RANGE[0]}–{AIR_TEMP_RANGE[1]}°C)")
    h = _last_float('data', 'AirEnv_Humidity')
    if h is not None and not (AIR_HUM_RANGE[0] <= h <= AIR_HUM_RANGE[1]):
        alarm(client, f"Air humidity out of range: {h:.0f}% (target {AIR_HUM_RANGE[0]}–{AIR_HUM_RANGE[1]}%)")

    # Dough moisture / hydration
    m = _last_float('data', 'DoughMoisture')
    if m is not None and not (DOUGH_MOIST_RANGE[0] <= m <= DOUGH_MOIST_RANGE[1]):
        alarm(client, f"Dough moisture out of range: {m:.0f}% (target {DOUGH_MOIST_RANGE[0]}–{DOUGH_MOIST_RANGE[1]}%)")
    hy = _last_float('data', 'Hydration')
    if hy is not None and not (HYDRATION_RANGE[0] <= hy <= HYDRATION_RANGE[1]):
        alarm(client, f"Hydration ratio out of range: {hy:.2f} (target {HYDRATION_RANGE[0]}–{HYDRATION_RANGE[1]})")

    # Volume
    v = _last_float('data', 'DoughVolume')
    if v is not None and v >= VOLUME_TARGET_MIN:
        alarm(client, f"Dough has proofed enough (volume ×{v:.2f} ≥ {VOLUME_TARGET_MIN}).")

    # Timer
    th = _last_float('data', 'TimerHours')
    if th is not None and th > PROOF_MAX_HOURS:
        alarm(client, f"Proofing time exceeded {th:.2f} h (> {PROOF_MAX_HOURS} h).")

    # Oven
    ot = _last_float('data', 'OvenTemp')
    if ot is not None and ot >= OVEN_READY_TEMP:
        alarm(client, f"Oven reached target temperature: {ot:.0f}°C (≥ {OVEN_READY_TEMP:.0f}°C).")

def check_Data(client):
    """שליחת פקודות לאקטואטורים אם שונו ברשומת iot_devices (special='changed')."""
    try:
        rows = da.check_changes('iot_devices')  # מחזיר רשימות dict-ים
        for row in rows:
            topic = row.get('dev_pub_topic') or f"{TOPIC_BASE}/actuator"
            dev_type = (row.get('dev_type') or '').lower()
            if dev_type == 'alarm':
                msg = 'Set temperature to: ' + str(row.get('temperature', ''))
                # פרסום ל-ALARM מכבד את דגלי הקונפיגורציה
                if SEND_EXTERNAL_ALARMS:
                    enable(client, ALARM_TOPIC, msg, retain=ALARM_RETAIN)
                else:
                    ic(f"[suppressed external alarm] {ALARM_TOPIC} {msg}")
                da.update_IOT_status(int(row['id']))
            else:
                msg = 'actuated'
                enable(client, topic, msg, retain=False)
                da.update_IOT_status(int(row['id']))
    except Exception as e:
        ic(f"check_Data error: {e}")

# ------------------ Main loop ------------------
def main():
    cname = "Manager-"
    client = client_init(cname)
    client.loop_start()
    # Subscribe לכל העץ תחת בסיס הנושא
    client.subscribe(f"{TOPIC_BASE}/#")

    try:
        while conn_time == 0:
            check_DB_for_change(client)  # בדיקת חריגות מחזורית
            time.sleep(manag_time)
            check_Data(client)           # הפעלת אקטואטורים לפי DB
            time.sleep(3)
        ic("con_time ending")
    except KeyboardInterrupt:
        client.disconnect()
        ic("interrrupted by keyboard")

    client.loop_stop()
    client.disconnect()
    ic("End manager run script")

if __name__ == "__main__":
    main()
