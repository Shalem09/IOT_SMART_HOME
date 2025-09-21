# data_acq.py — DB bootstrap & seeding (drops iot_devices on init)
import os
import sqlite3
from datetime import datetime
from contextlib import closing

from init import db_name as INIT_DB_NAME, db_init as INIT_DB_INIT, comm_topic as COMM_TOPIC

def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

def connect(db_path: str) -> sqlite3.Connection:
    ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

DROP_IOT_DEVICES_TABLE = "DROP TABLE IF EXISTS iot_devices;"

CREATE_IOT_DEVICES_TABLE = """
CREATE TABLE IF NOT EXISTS iot_devices (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL UNIQUE,
    status            TEXT,
    units             TEXT,
    last_updated      TEXT,
    update_interval   INTEGER,
    Dream_GuardCarId  TEXT,
    placed            TEXT,
    dev_type          TEXT,
    enabled           TEXT,
    state             TEXT,
    mode              TEXT,
    fan               TEXT,
    temperature       TEXT,
    dev_pub_topic     TEXT,
    dev_sub_topic     TEXT,
    special           TEXT
);
"""

CREATE_IOT_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS iot_data (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    device_name  TEXT NOT NULL,
    metric       TEXT NOT NULL,
    value        REAL,
    units        TEXT,
    FOREIGN KEY (device_name) REFERENCES iot_devices(name)
);
"""

CREATE_IOT_ALERTS_TABLE = """
CREATE TABLE IF NOT EXISTS iot_alerts (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    level    TEXT,
    message  TEXT
);
"""

INSERT_OR_REPLACE_IOT_DEVICE = """
INSERT INTO iot_devices(
    name, status, units, last_updated, update_interval,
    Dream_GuardCarId, placed, dev_type, enabled, state, mode, fan,
    temperature, dev_pub_topic, dev_sub_topic, special
) VALUES (:name, :status, :units, :last_updated, :update_interval,
          :Dream_GuardCarId, :placed, :dev_type, :enabled, :state, :mode, :fan,
          :temperature, :dev_pub_topic, :dev_sub_topic, :special)
ON CONFLICT(name) DO UPDATE SET
    status          = excluded.status,
    units           = excluded.units,
    last_updated    = excluded.last_updated,
    update_interval = excluded.update_interval,
    Dream_GuardCarId= excluded.Dream_GuardCarId,
    placed          = excluded.placed,
    dev_type        = excluded.dev_type,
    enabled         = excluded.enabled,
    state           = excluded.state,
    mode            = excluded.mode,
    fan             = excluded.fan,
    temperature     = excluded.temperature,
    dev_pub_topic   = excluded.dev_pub_topic,
    dev_sub_topic   = excluded.dev_sub_topic,
    special         = excluded.special
"""

def create_schema(conn: sqlite3.Connection, force_drop_iot_devices: bool) -> None:
    with conn:
        if force_drop_iot_devices:
            conn.execute(DROP_IOT_DEVICES_TABLE)   # מבטיח סכימה חדשה ל-iot_devices
        conn.execute(CREATE_IOT_DEVICES_TABLE)
        conn.execute(CREATE_IOT_DATA_TABLE)
        conn.execute(CREATE_IOT_ALERTS_TABLE)

def upsert_device(conn: sqlite3.Connection, **kw) -> int:
    with conn:
        conn.execute(INSERT_OR_REPLACE_IOT_DEVICE, kw)
    row = conn.execute("SELECT id FROM iot_devices WHERE name = ?", (kw["name"],)).fetchone()
    return int(row["id"]) if row else -1

def list_devices(conn: sqlite3.Connection):
    return conn.execute("SELECT * FROM iot_devices ORDER BY id").fetchall()

if __name__ == "__main__":
    print(f"{timestamp()}  data acq|> pp: 'Conected to version: {sqlite3.version}'")
    print(f"{timestamp()}  data acq|> DB path: {INIT_DB_NAME}")

    ensure_parent_dir(INIT_DB_NAME)
    with closing(connect(INIT_DB_NAME)) as conn:
        if INIT_DB_INIT:
            print(f"{timestamp()}  data acq|> Initializing DB schema (dropping iot_devices)…")
            create_schema(conn, force_drop_iot_devices=True)

            # זרעים (devices) בסיסיים
            upsert_device(
                conn,
                name="alarm",
                status="off",
                units="N",
                last_updated=timestamp(),
                update_interval=300,
                Dream_GuardCarId="DG-001",
                placed="left front",
                dev_type="alarm",
                enabled="false",
                state="cooling",
                mode="mode",
                fan="fan",
                temperature="32",
                dev_pub_topic=COMM_TOPIC + "ala-1/pub",
                dev_sub_topic=COMM_TOPIC + "ala-1/sub",
                special="changed",
            )
            upsert_device(
                conn,
                name="ElecMeter",
                status="ok",
                units="kWh",
                last_updated=timestamp(),
                update_interval=60,
                Dream_GuardCarId="DG-002",
                placed="panel",
                dev_type="meter",
                enabled="true",
                state="idle",
                mode="normal",
                fan="na",
                temperature="na",
                dev_pub_topic=COMM_TOPIC + "elec-1/pub",
                dev_sub_topic=COMM_TOPIC + "elec-1/sub",
                special="",
            )
            upsert_device(
                conn,
                name="DHT-1",
                status="ok",
                units="Celsius",
                last_updated=timestamp(),
                update_interval=30,
                Dream_GuardCarId="DG-003",
                placed="room",
                dev_type="dht",
                enabled="true",
                state="idle",
                mode="normal",
                fan="na",
                temperature="25",
                dev_pub_topic=COMM_TOPIC + "dht-1/pub",
                dev_sub_topic=COMM_TOPIC + "dht-1/sub",
                special="",
            )
            upsert_device(
                conn,
                name="Motion",
                status="ok",
                units="km",
                last_updated=timestamp(),
                update_interval=15,
                Dream_GuardCarId="DG-004",
                placed="room",
                dev_type="motion",
                enabled="true",
                state="idle",
                mode="normal",
                fan="na",
                temperature="na",
                dev_pub_topic=COMM_TOPIC + "mot-1/pub",
                dev_sub_topic=COMM_TOPIC + "mot-1/sub",
                special="",
            )
            print(f"{timestamp()}  data acq|> DB initialized & devices seeded.")
        else:
            # במצב רגיל רק וידוא סכימה (בלי דרופ)
            create_schema(conn, force_drop_iot_devices=False)

        rows = list_devices(conn)
        if rows:
            print(f"{timestamp()}  data acq|> Devices in DB:")
            for r in rows:
                print("  -", dict(r))
        else:
            print(f"{timestamp()}  data acq|> No devices found. (Did you set db_init=True for first run?)")
# ==== helpers for manager.py ====
import pandas as _pd

def add_IOT_data(device_name: str, ts: str, value, units: str = ''):
    """Insert a single measurement into iot_data. metric=name for תאימות לאחור."""
    try:
        v = float(value)
    except Exception:
        v = None
    conn = connect(INIT_DB_NAME)
    try:
        with conn:
            conn.execute(
                "INSERT INTO iot_data (ts, device_name, metric, value, units) VALUES (?, ?, ?, ?, ?)",
                (ts, device_name, device_name, v, units)
            )
    finally:
        conn.close()

def fetch_data(db_path: str, table_alias: str, metric: str) -> _pd.DataFrame:
    """Return a DataFrame of (ts, value) for given metric from iot_data."""
    conn = connect(INIT_DB_NAME)
    try:
        rows = conn.execute(
            "SELECT ts, value FROM iot_data WHERE metric = ? ORDER BY ts ASC",
            (metric,)
        ).fetchall()
        df = _pd.DataFrame([dict(r) for r in rows]) if rows else _pd.DataFrame(columns=['ts','value'])
        return df
    finally:
        conn.close()

def check_changes(table_name: str = 'iot_devices'):
    """Return devices marked as changed."""
    conn = connect(INIT_DB_NAME)
    try:
        rows = conn.execute(
            "SELECT * FROM iot_devices WHERE special = 'changed' ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def update_IOT_status(device_id: int):
    """Clear 'special' flag and update last_updated."""
    conn = connect(INIT_DB_NAME)
    try:
        with conn:
            conn.execute(
                "UPDATE iot_devices SET special = '', last_updated = ? WHERE id = ?",
                (timestamp(), device_id)
            )
    finally:
        conn.close()
# ==== end helpers ====
