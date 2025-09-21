# proofing_dashboard.py — Dough Proofing Dashboard
# Alerts + beep on any threshold violation; alarm text goes to ALARMS (not Timer/Oven).

import re, sys, time
import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt

try:
    from init import (
        broker_ip, broker_port, comm_topic,
        PROOF_TEMP_MIN, PROOF_TEMP_MAX,
        PROOF_HUM_MIN, PROOF_HUM_MAX,
        DOUGH_MOIST_MIN, DOUGH_MOIST_MAX,
        RISE_TARGET_PCT
    )
except Exception:
    broker_ip = "broker.hivemq.com"
    broker_port = 1883
    comm_topic = "pr/Proofing/BakeryA/"
    PROOF_TEMP_MIN, PROOF_TEMP_MAX = 27.0, 32.0
    PROOF_HUM_MIN,  PROOF_HUM_MAX  = 70.0, 85.0
    DOUGH_MOIST_MIN, DOUGH_MOIST_MAX = 55.0, 65.0
    RISE_TARGET_PCT = 75.0

TOPIC_BASE = comm_topic.rstrip("/")
TOPICS = {
    "env":   f"{TOPIC_BASE}/env-1/pub",
    "dough": f"{TOPIC_BASE}/doughH-1/pub",
    "rise":  f"{TOPIC_BASE}/rise-1/pub",
    "timer": f"{TOPIC_BASE}/timer-1/pub",
    "alarm": f"{TOPIC_BASE}/alarm",
}

def safe_beep(root):
    try:
        if sys.platform.startswith("win"):
            import winsound
            winsound.Beep(880, 250)
        else:
            root.bell()
    except:
        try: root.bell()
        except: pass

class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dough Proofing — Dashboard")
        self.geometry("560x340")
        self.resizable(False, False)
        self.configure(padx=10, pady=10)

        s = ttk.Style(self)
        try: s.theme_use("vista")
        except: pass

        self.var_temp  = tk.StringVar(value="—")
        self.var_hum   = tk.StringVar(value="—")
        self.var_dhm   = tk.StringVar(value="—")
        self.var_rise  = tk.StringVar(value="—")
        self.var_timer = tk.StringVar(value="—")
        self.var_alarm = tk.StringVar(value="—")

        row = 0
        ttk.Label(self, text="Air Temperature (°C):", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w")
        self.e_temp = ttk.Entry(self, textvariable=self.var_temp, state="readonly", width=12); self.e_temp.grid(row=row, column=1, sticky="w"); row += 1

        ttk.Label(self, text="Air Humidity (%RH):", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w")
        self.e_hum = ttk.Entry(self, textvariable=self.var_hum, state="readonly", width=12); self.e_hum.grid(row=row, column=1, sticky="w")
        self.pb_hum = ttk.Progressbar(self, orient="horizontal", length=220, mode="determinate", maximum=100); self.pb_hum.grid(row=row, column=2, padx=8); row += 1

        ttk.Label(self, text="Dough Moisture (%):", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w")
        self.e_dhm = ttk.Entry(self, textvariable=self.var_dhm, state="readonly", width=12); self.e_dhm.grid(row=row, column=1, sticky="w")
        self.pb_dhm = ttk.Progressbar(self, orient="horizontal", length=220, mode="determinate", maximum=100); self.pb_dhm.grid(row=row, column=2, padx=8); row += 1

        ttk.Label(self, text="Dough Rise (%):", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w")
        self.e_rise = ttk.Entry(self, textvariable=self.var_rise, state="readonly", width=12); self.e_rise.grid(row=row, column=1, sticky="w")
        self.pb_rise = ttk.Progressbar(self, orient="horizontal", length=220, mode="determinate", maximum=100); self.pb_rise.grid(row=row, column=2, padx=8); row += 1

        ttk.Label(self, text="Timer / Oven:", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w")
        self.e_timer = ttk.Entry(self, textvariable=self.var_timer, state="readonly", width=32); self.e_timer.grid(row=row, column=1, columnspan=2, sticky="w"); row += 1

        ttk.Label(self, text="Alarms:", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w")
        self.e_alarm = ttk.Entry(self, textvariable=self.var_alarm, state="readonly", width=50); self.e_alarm.grid(row=row, column=1, columnspan=2, sticky="w"); row += 1

        ttk.Separator(self, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=(6,8)); row += 1
        ttk.Label(
            self,
            text="Target Values:",
            font=("Segoe UI", 10, "bold"),
            foreground="#333"
        ).grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        # טמפרטורה
        ttk.Label(
            self,
            text=f"    • Temp: {PROOF_TEMP_MIN}-{PROOF_TEMP_MAX}°C",
            foreground="#555"
        ).grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        # לחות
        ttk.Label(
            self,
            text=f"    • Humidity: {PROOF_HUM_MIN}-{PROOF_HUM_MAX}%",
            foreground="#555"
        ).grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        # לחות בצק
        ttk.Label(
            self,
            text=f"    • Dough Moisture: {DOUGH_MOIST_MIN}-{DOUGH_MOIST_MAX}%",
            foreground="#555"
        ).grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        # אחוז תפיחה
        ttk.Label(
            self,
            text=f"    • Rise: ≥ {RISE_TARGET_PCT}%",
            foreground="#555"
        ).grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        # anti-spam (מצב אחרון)
        self.last_alarm = {"temp": False, "hum": False, "dough": False, "rise": False}
        # “חימוש” — ההתראה תופעל רק אחרי שמתקבלת מדידה חיה ראשונה
        self.armed = {"env": False, "dough": False, "rise": False}

    def set_bg(self, widget, ok: bool):
        try: widget.configure(background=("#d1ffd1" if ok else "#ffd6d6"))
        except: pass

    def _alarm_transition(self, key: str, now_bad: bool, msg_bad: str, msg_ok: str | None = None):
        was_bad = self.last_alarm.get(key, False)
        if now_bad and not was_bad:
            self.var_alarm.set(msg_bad)
            safe_beep(self)
        elif (not now_bad) and was_bad:
            if msg_ok:
                self.var_alarm.set(msg_ok)
        self.last_alarm[key] = now_bad

    # ---- הוספת suppress_alarm להודעה הראשונה ----
    def update_env(self, temp, hum, suppress_alarm: bool = False):
        self.var_temp.set(f"{temp:.1f}")
        self.var_hum.set(f"{hum:.0f}")
        self.pb_hum["value"] = max(0, min(100, hum))

        ok_t = PROOF_TEMP_MIN <= temp <= PROOF_TEMP_MAX
        ok_h = PROOF_HUM_MIN  <= hum  <= PROOF_HUM_MAX

        self.set_bg(self.e_temp, ok_t)
        self.set_bg(self.e_hum,  ok_h)

        if not suppress_alarm:
            self._alarm_transition(
                "temp", not ok_t,
                f"Air temperature out of range: {temp:.1f}°C (target {PROOF_TEMP_MIN}–{PROOF_TEMP_MAX}°C)",
                "Air temperature back in range"
            )
            self._alarm_transition(
                "hum", not ok_h,
                f"Air humidity out of range: {hum:.0f}% (target {PROOF_HUM_MIN}–{PROOF_HUM_MAX}%)",
                "Air humidity back in range"
            )

    def update_dough_moist(self, m, suppress_alarm: bool = False):
        self.var_dhm.set(f"{m:.0f}")
        self.pb_dhm["value"] = max(0, min(100, m))
        ok = DOUGH_MOIST_MIN <= m <= DOUGH_MOIST_MAX
        self.set_bg(self.e_dhm, ok)
        if not suppress_alarm:
            self._alarm_transition(
                "dough", not ok,
                f"Dough moisture out of range: {m:.0f}% (target {DOUGH_MOIST_MIN}–{DOUGH_MOIST_MAX}%)",
                "Dough moisture back in range"
            )

    def update_rise(self, r, suppress_alarm: bool = False):
        self.var_rise.set(f"{r:.0f}")
        self.pb_rise["value"] = max(0, min(100, r))
        ok = r >= RISE_TARGET_PCT
        self.set_bg(self.e_rise, ok)
        if not suppress_alarm:
            self._alarm_transition(
                "rise", not ok,
                f"Dough rise below target: {r:.0f}% (target ≥ {RISE_TARGET_PCT}%)",
                "Dough rise reached target"
            )

    def update_timer(self, msg, do_beep=False):
        self.var_timer.set(msg)
        if do_beep:
            safe_beep(self)
            try:
                orig = self.e_alarm.cget("background")
                self.var_alarm.set("🔥 Oven Ready / Timer Done")
                self.e_alarm.configure(background="#ffd6d6")
                self.after(2000, lambda: self.e_alarm.configure(background=orig))
            except: pass

# ---------- MQTT ----------
def run():
    ui = Dashboard()

    def on_connect(client, userdata, flags, rc, properties=None):
        for _, t in TOPICS.items():
            client.subscribe(t, qos=0)

    env_re   = re.compile(r"Temperature:\s*([-+]?\d+(\.\d+)?)\s+Humidity:\s*([-+]?\d+(\.\d+)?)", re.I)
    moist_re = re.compile(r"Dough\s+Moisture:\s*([-+]?\d+(\.\d+)?)", re.I)
    rise_re  = re.compile(r"Dough\s+Rise:\s*([-+]?\d+(\.\d+)?)", re.I)
    timer_rem_re  = re.compile(r"Timer\s+remaining:\s*(\d+)", re.I)
    oven_ready_re = re.compile(r"Oven\s+Ready:\s*1", re.I)

    def on_message(client, userdata, msg):
        topic = msg.topic

        # התעלמות מהודעות Retained ישנות
        if getattr(msg, "retain", False):
            return

        try:
            text = msg.payload.decode("utf-8", "ignore")
        except:
            return

        if topic == TOPICS["env"]:
            m = env_re.search(text)
            if m:
                t = float(m.group(1)); h = float(m.group(3))
                first = not ui.armed["env"]
                ui.armed["env"] = True
                ui.update_env(t, h, suppress_alarm=first)

        elif topic == TOPICS["dough"]:
            m = moist_re.search(text)
            if m:
                val = float(m.group(1))
                first = not ui.armed["dough"]
                ui.armed["dough"] = True
                ui.update_dough_moist(val, suppress_alarm=first)

        elif topic == TOPICS["rise"]:
            m = rise_re.search(text)
            if m:
                val = float(m.group(1))
                first = not ui.armed["rise"]
                ui.armed["rise"] = True
                ui.update_rise(val, suppress_alarm=first)

        elif topic == TOPICS["timer"]:
            if oven_ready_re.search(text):
                ui.update_timer("Oven Ready ✓", do_beep=True)
            else:
                m = timer_rem_re.search(text)
                if m:
                    sec = int(m.group(1))
                    ui.update_timer(f"{sec} sec remaining", do_beep=(sec == 0))

        elif topic == TOPICS["alarm"]:
            # אם מקור חיצוני שולח טקסט התראה – מציגים אותו ישירות ב-ALARM
            ui.var_alarm.set(text)

    client = mqtt.Client(
        client_id=f"Dashboard-{int(time.time()*1000)%100000}",
        clean_session=True,
        protocol=mqtt.MQTTv311,
        transport="tcp",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(broker_ip, int(broker_port), keepalive=60)
    client.loop_start()
    ui.mainloop()
    client.loop_stop(); client.disconnect()

if __name__ == "__main__":
    run()
