# main_service.py - MQTT -> buffer -> Neo4j + KPI, print snapshot every 2s

import os
import sys
import time
from datetime import datetime
import common
import paho.mqtt.client as mqtt

import event_buffer
import kpi_calculator
import neo4j_writer

CONFIG = common.load_json("config.json")
MQTT_BROKER_HOST = CONFIG["mqtt_broker_host"]
MQTT_BROKER_PORT = CONFIG["mqtt_broker_port"]
BUFFER_CFG = CONFIG.get("event_buffer", {})
KPI_CFG = CONFIG.get("kpi_config", {})
# --replay for replay_events test
OBS_MODE = "replay" if "--replay" in sys.argv else KPI_CFG.get("observation_time_mode", "realtime")

buffer = event_buffer.EventBuffer(
    window_ms=BUFFER_CFG.get("window_ms", 300),
)
kpi = kpi_calculator.KpiCalculator(
    observation_time_mode=OBS_MODE,
    finish_events=KPI_CFG.get("finish_events", ["FINISH"]),
    scrap_events=KPI_CFG.get("scrap_events", ["SCRAP"]),
)


def on_connect(client, userdata, flags, rc):
    print("[main_service] Connected to MQTT, code", rc)
    topic = common.render_topic("component_event", "+", "all")
    client.subscribe(topic, qos=2)


def on_message(client, userdata, msg):
    context, source_id, target_id = common.parse_topic(msg.topic)
    payload = msg.payload.decode("utf-8")
    if context == "component_event":
        event = common.deserialize_object(payload)
        buffer.add(event)


def _print_kpi_snapshot(snap: dict, log_file=None):
    """Print KPI snapshot, optionally write to log_file."""
    lines = []
    lines.append("[KPI] throughput={}, finished={}, scrap={}, obs_time={}s, wip={}, avg_flow_time={}s".format(
        snap["throughput"], snap["finished_count"], snap["scrap_count"],
        snap["observation_time_sec"], snap["wip"], snap["avg_flow_time_sec"],
    ))
    for sid, probs in snap.get("state_probability", {}).items():
        util = snap["utilization"].get(sid, 0)
        lines.append("  {}".format(sid))
        lines.append("    Utilization: {:.2f}".format(util))
        lines.append("    Loading: {:.2f}  Blocked: {:.2f}  Idle: {:.2f}  Processing: {:.2f}  Unloading: {:.2f}".format(
            probs.get("loading", 0), probs.get("blocked", 0), probs.get("idle", 0),
            probs.get("processing", 0), probs.get("unloading", 0),
        ))
    text = "\n".join(lines)
    print(text)
    if log_file:
        log_file.write(text + "\n")
        log_file.flush()


def _process_ready_events():
    """Flush buffer, write to Neo4j, update KPI."""
    ready = buffer.flush_ready()
    for ev in ready:
        try:
            neo4j_writer.write_event_to_graph(ev)
        except Exception as e:
            print("[main_service] Neo4j write error:", e)
        kpi.on_event(ev)


mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER_HOST, port=MQTT_BROKER_PORT)
mqtt_client.loop_start()

KPI_PRINT_INTERVAL = 2.0
_last_print_ts = 0.0

LOG_FOLDER = CONFIG.get("log_folder", "event-logs")
LOG_TIME = datetime.now().strftime("%y%m%d_%H%M%S")
LOG_FILE = "kpi_log_{}.txt".format(LOG_TIME)
LOG_PATH = os.path.normpath(os.path.join(LOG_FOLDER, LOG_FILE))
os.makedirs(LOG_FOLDER, exist_ok=True)
kpi_log_file = open(LOG_PATH, "w", encoding="utf-8")

def _log(msg: str):
    print(msg)
    kpi_log_file.write(msg + "\n")
    kpi_log_file.flush()

_log("[main_service] Started. Buffer + Neo4j + KPI. Ctrl+C to stop.")
_log("[main_service] KPI log: {}".format(LOG_PATH))
try:
    while True:
        time.sleep(0.3)
        _process_ready_events()
        now = time.time()
        if now - _last_print_ts >= KPI_PRINT_INTERVAL:
            _last_print_ts = now
            snap = kpi.get_snapshot()
            _print_kpi_snapshot(snap, kpi_log_file)
except KeyboardInterrupt:
    pass
finally:
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    neo4j_writer.close()
    _log("[main_service] Stopped.")
    kpi_log_file.close()
