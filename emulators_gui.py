# emulators_gui.py – Proofing-ready MQTT emulators:
# AirEnv, DoughMoisture, DoughRise, ProofTimer (טיימר + Beep), Alarm (מנוי)

import tkinter as tk
from tkinter import ttk, messagebox
import queue, time
import paho.mqtt.client as mqtt

# ===== ברירת מחדל/ייבוא הגדרות =====
try:
    from init import broker_ip, broker_port, comm_topic
except Exception:
    broker_ip  = "broker.hivemq.com"
    broker_port = "1883"
    comm_topic = "pr/Proofing/BakeryA/"

TOPIC_BASE   = comm_topic.rstrip("/")
BROKER_HOST  = broker_ip
BROKER_PORT  = int(str(broker_port))

DEFAULT_TOPICS = {
    "env":   f"{TOPIC_BASE}/env-1/pub",
    "dough": f"{TOPIC_BASE}/doughH-1/pub",
    "rise":  f"{TOPIC_BASE}/rise-1/pub",
    "timer": f"{TOPIC_BASE}/timer-1/pub",
    "alarm": f"{TOPIC_BASE}/alarm",
}

# ---------- MQTT utils ----------
def make_client(client_id: str, on_message=None, on_log=None):
    client = mqtt.Client(
        client_id=client_id,
        clean_session=True,
        protocol=mqtt.MQTTv311,
        transport="tcp",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    if on_message: client.on_message = on_message
    if on_log:     client.on_log     = on_log
    return client

# ---------- Base window ----------
class BaseWindow(tk.Toplevel):
    def __init__(self, root, title="IOT Emulator", size="340x220", default_topic=""):
        super().__init__(root)
        self.title(title); self.geometry(size); self.resizable(False, False)
        self.configure(padx=10, pady=10)

        # מצב פנימי
        self.client = None
        self.connected = False
        self.enabled = False
        self.pub_every_ms = 2000
        self._after_job = None

        # נשתמש במשתנה פנימי במקום Entry ל-topic
        self.topic = default_topic

        # עיצוב בסיסי
        s = ttk.Style(self)
        try: s.theme_use("vista")
        except: pass

        ttk.Label(self, text=title, font=("Segoe UI",10,"bold")).grid(row=0, column=0, columnspan=2, sticky="w")

        self.btn_enable = ttk.Button(self, text="Enable/Connect", command=self.toggle_enable)
        self.btn_enable.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6,8))

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.columnconfigure(1, weight=1)

    def toggle_enable(self):
        if not self.connected:
            self.connect()
        self.enabled = not self.enabled
        self.btn_enable.config(text=("Disable" if self.enabled else "Enable/Connect"))
        if self.enabled:
            self.on_enabled()
        else:
            self.on_disabled()

    def connect(self):
        if self.connected:
            return
        self.client = make_client(f"{self.title()}-{int(time.time()*1000)%10000}",
                                  on_message=self._on_message, on_log=self._on_log)
        try:
            self.client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            self.client.loop_start()
            self.connected = True
        except Exception as e:
            messagebox.showerror("MQTT", f"Connect failed: {e}")
            self.connected = False

    def on_enabled(self):  # לכל חלון יש מימוש משלו
        pass

    def on_disabled(self):
        if self._after_job:
            try: self.after_cancel(self._after_job)
            except: pass
            self._after_job = None

    def publish(self, topic, payload):
        if self.connected:
            self.client.publish(topic, payload)

    def _on_message(self, client, userdata, msg):  # למנויים בלבד
        pass

    def _on_log(self, client, userdata, level, buf):
        pass

    def on_close(self):
        try: self.on_disabled()
        except: pass
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
        except: pass
        self.destroy()

# ---------- AirEnv ----------
class AirEnvWindow(BaseWindow):
    def __init__(self, root):
        super().__init__(root, title="AirEnv", size="360x190", default_topic=DEFAULT_TOPICS["env"])

        ttk.Label(self, text="Temperature (°C)").grid(row=3, column=0, sticky="w", pady=(6,0))
        self.e_temp = ttk.Entry(self); self.e_temp.grid(row=3, column=1, sticky="ew", pady=(6,0))
        self.e_temp.insert(0, "30")

        ttk.Label(self, text="Humidity (%RH)").grid(row=4, column=0, sticky="w")
        self.e_hum = ttk.Entry(self); self.e_hum.grid(row=4, column=1, sticky="ew")
        self.e_hum.insert(0, "78")

    def on_enabled(self):
        def tick():
            topic = self.topic
            temp = self.e_temp.get().strip()
            hum  = self.e_hum.get().strip()
            msg  = f"From: AirEnv Temperature: {temp} Humidity: {hum}"
            self.publish(topic, msg)
            self._after_job = self.after(self.pub_every_ms, tick)
        tick()

# ---------- DoughMoisture ----------
class DoughMoistureWindow(BaseWindow):
    def __init__(self, root):
        super().__init__(root, title="DoughMoisture", size="360x170", default_topic=DEFAULT_TOPICS["dough"])

        ttk.Label(self, text="Moisture (%)").grid(row=3, column=0, sticky="w", pady=(6,0))
        self.e_val = ttk.Entry(self); self.e_val.grid(row=3, column=1, sticky="ew", pady=(6,0))
        self.e_val.insert(0, "60")

    def on_enabled(self):
        def tick():
            topic = self.topic
            m = self.e_val.get().strip()
            msg = f"Dough Moisture: {m}"
            self.publish(topic, msg)
            self._after_job = self.after(self.pub_every_ms, tick)
        tick()

# ---------- DoughRise ----------
class DoughRiseWindow(BaseWindow):
    def __init__(self, root):
        super().__init__(root, title="DoughRise", size="360x170", default_topic=DEFAULT_TOPICS["rise"])

        ttk.Label(self, text="Rise (%)").grid(row=3, column=0, sticky="w", pady=(6,0))
        self.e_val = ttk.Entry(self); self.e_val.grid(row=3, column=1, sticky="ew", pady=(6,0))
        self.e_val.insert(0, "40")

    def on_enabled(self):
        def tick():
            topic = self.topic
            r = self.e_val.get().strip()
            msg = f"Dough Rise: {r}"
            self.publish(topic, msg)
            self._after_job = self.after(self.pub_every_ms, tick)
        tick()

# ---------- ProofTimer (אין שינוי ערך ב-GUI; הספירה נעשית בדאשבורד) ----------
class ProofTimerWindow(BaseWindow):
    def __init__(self, root):
        super().__init__(root, title="ProofTimer", size="380x210", default_topic=DEFAULT_TOPICS["timer"])

        ttk.Label(self, text="Remaining (sec)").grid(row=3, column=0, sticky="w", pady=(6,0))
        self.e_sec = ttk.Entry(self); self.e_sec.grid(row=3, column=1, sticky="ew", pady=(6,0))
        self.e_sec.insert(0, "900")

        self.btn_beep = ttk.Button(self, text="Oven Ready (Beep)", command=self.send_beep)
        self.btn_beep.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8,0))

        self.pub_every_ms = 1000
        self._rem = None  # נשמר פנימית לצורך ספירה — בלי לשנות את ה-Entry

    def on_enabled(self):
        # אתחול rem פנימי מערך ה-Entry — ה-Entry לא יתעדכן בהמשך
        try:
            self._rem = int(self.e_sec.get().strip())
        except:
            self._rem = 0

        def tick():
            topic = self.topic
            # פרסום הערך הנוכחי — הדאשבורד יספור
            self.publish(topic, f"Timer remaining: {max(0, self._rem)}")

            self._rem = max(0, self._rem - 1)
            if self._rem == 0:
                # שליחת הודעת Oven Ready פעם אחת לסגירת הלופ והפעלת ההתראה
                self.publish(topic, "Oven Ready: 1")
                self.enabled = False
                self.btn_enable.config(text="Enable/Connect")
                return
            self._after_job = self.after(self.pub_every_ms, tick)

        tick()

    def send_beep(self):
        self.publish(self.topic, "Oven Ready: 1")

# ---------- Alarm (Subscriber) ----------
class AlarmWindow(BaseWindow):
    def __init__(self, root):
        super().__init__(root, title="Alarm", size="380x180", default_topic=DEFAULT_TOPICS["alarm"])

        ttk.Label(self, text="Status").grid(row=3, column=0, sticky="w", pady=(6,0))
        self.var_status = tk.StringVar(value="—")
        self.e_status = ttk.Entry(self, textvariable=self.var_status, state="readonly")
        self.e_status.grid(row=3, column=1, sticky="ew", pady=(6,0))

        self.msg_q = queue.Queue()

    def _on_message(self, client, userdata, msg):
        try:
            self.msg_q.put((msg.topic, msg.payload.decode("utf-8","ignore")))
        except:
            pass

    def on_enabled(self):
        topic = self.topic
        # נרשמים לטופיק ההתראות
        self.client.subscribe(topic, qos=0)

        def pump():
            try:
                while True:
                    _, m = self.msg_q.get_nowait()
                    self.var_status.set(m[:64])
            except queue.Empty:
                pass
            self._after_job = self.after(150, pump)
        pump()

# ---------- App ----------
def main():
    root = tk.Tk(); root.withdraw()
    AirEnvWindow(root)
    DoughMoistureWindow(root)
    DoughRiseWindow(root)
    ProofTimerWindow(root)
    AlarmWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
