# IoT Smart Home – Dough Proofing System

A small IoT project that demonstrates **real-time monitoring and control of a dough proofing process** (bakery setting).  
It uses MQTT to pass messages between **emulators** (simulated sensors/actuators) and a **Python dashboard** that visualizes values, highlights out-of-range conditions, and shows alarms.

---

## ✨ What’s inside
- **MQTT Emulators** (Python/Tkinter):
  - `Env` – publishes **Temperature** and **Humidity** (DHT-like).
  - `Dough Moisture` – publishes dough moisture %.
  - `ProofTimer` – accepts seconds → publishes *Timer start* and *Oven Ready*; can also publish *remaining* ticks.
- **Dashboard GUI** (`proofing_dashboard.py`, Tkinter):
  - Shows air Temp/Humidity, Dough Moisture, Rise %, **Timer**, and **Alarms**.
  - Local **countdown** starts automatically when it receives `Timer start: N`.
  - Ignores external “remaining” messages while a local countdown is running.
- **Topics & Alarms**:
  - Subscribes to sensor topics and **Alarm** topic; colors fields if values are out of range.

---

## 🧩 Tech Stack
- Python 3.10+
- Tkinter, `paho-mqtt`
- (Optional) PyQt5, pyqtgraph, pandas/numpy/matplotlib for extended features
- MQTT broker (e.g., public HiveMQ or local Mosquitto)

---

## 📦 Installation (Windows / macOS / Linux)

```bash
# 1) Clone
git clone https://github.com/Shalem09/IOT_SMART_HOME.git
cd IOT_SMART_HOME

# 2) Create & activate virtual env
# Windows:
py -m venv .venv
.\.venv\Scripts\activate
# macOS/Linux:
# python3 -m venv .venv
# source .venv/bin/activate

# 3) Install minimal deps
pip install --upgrade pip
pip install paho-mqtt
# Optional extras (GUI/plots etc.):
# pip install PyQt5 pyqtgraph pandas numpy matplotlib icecream
```

> **Note:** The repo ignores virtual environments and local DB files; set up your own venv locally.

---

## ⚙️ Configuration
Edit `init.py` (or keep defaults):

```python
broker_ip   = "broker.hivemq.com"
broker_port = 1883
comm_topic  = "pr/Proofing/BakeryA/"  # topic prefix (no trailing slash needed in code)
```

The dashboard subscribes to:

```
{comm_topic}/env-1/pub
{comm_topic}/doughH-1/pub
{comm_topic}/rise-1/pub
{comm_topic}/timer-1/pub
{comm_topic}/alarm
```

---

## 🚀 Running

### 1) Start emulators
```bash
python emulators_gui.py
```
Open **ProofTimer** (type seconds and press Enter), **Env**, **Dough Moisture** as needed.

### 2) Start dashboard
Open a second terminal, activate the same venv, then:
```bash
python proofing_dashboard.py
```

The **Timer** field will show `N sec remaining` and count down locally after receiving `Timer start: N`.  
Press **Oven Ready (Beep)** in the ProofTimer emulator to publish `Oven Ready: 1` → the dashboard shows **Oven Ready ✓**.

---

## 📨 Message Formats (examples)

- Env (DHT-like):  
  `Temperature: 28.5 Humidity: 72.0`

- Dough Moisture:  
  `Dough Moisture: 63.0`

- Rise:  
  `Dough Rise: 78.0`

- Timer control:  
  - Start: `Timer start: 67`  
  - Remaining (optional ticks from emulator): `Timer remaining: 64`  
  - Ready: `Oven Ready: 1`

---

## 🧪 Tips & Troubleshooting

- **`ModuleNotFoundError: No module named 'paho'`**  
  Activate venv and install deps:
  ```bash
  .\.venv\Scripts\activate    # or: source .venv/bin/activate
  pip install paho-mqtt
  ```

- **Alarm shows old text on startup**  
  That’s likely a **retained** message in the broker. Either publish an empty retained message to clear:
  ```python
  client.publish(f"{comm_topic.rstrip('/')}/alarm", payload="", retain=True)
  ```
  or ignore the first retained message in code.

- **No connection to broker**  
  Check `broker_ip`, `broker_port`, firewall, and that topics match on both sides.

---

## 📁 Suggested Structure

```
IOT_SMART_HOME/
├─ emulators_gui.py         # MQTT emulators (Env, Dough, ProofTimer)
├─ proofing_dashboard.py    # Main dashboard
├─ init.py                  # Broker/topics + thresholds
├─ data/                    # (local DB files if used)
├─ requirements.txt         # (optional)
└─ README.md
```
