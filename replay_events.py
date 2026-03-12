# replay_events.py - send event log CSV to MQTT for main_service test

import time
from datetime import datetime
import common
import paho.mqtt.client as mqtt
import pandas

CONFIG = common.load_json("config.json")
MQTT_BROKER_HOST = CONFIG["mqtt_broker_host"]
MQTT_BROKER_PORT = CONFIG["mqtt_broker_port"]

LOG_PATH = "event-logs/event_log_260306_104030.csv"
SPEED_FACTOR = 10  # 10x speed, use 1 for real-time


def main(log_path: str = LOG_PATH, speed: float = SPEED_FACTOR):
    df = pandas.read_csv(log_path)
    df = df.sort_values("time")
    events = df.to_dict("records")

    client = mqtt.Client()
    client.connect(MQTT_BROKER_HOST, port=MQTT_BROKER_PORT)
    client.loop_start()

    print(f"Replaying {len(events)} events from {log_path}, speed={speed}x")
    t0 = time.time()
    prev_ts = None
    for ev in events:
        ts_str = ev.get("time")
        if prev_ts is not None and ts_str:
            try:
                curr = datetime.fromisoformat(ts_str).timestamp()
                delay = (curr - prev_ts) / speed
                if delay > 0:
                    time.sleep(delay)
                prev_ts = curr
            except Exception:
                prev_ts = None
                time.sleep(0.1)
        else:
            try:
                prev_ts = datetime.fromisoformat(ts_str).timestamp()
            except Exception:
                pass
            time.sleep(0.05)

        topic = common.render_topic("component_event", ev["component_id"], "all")
        payload = common.serialize_object(ev)
        client.publish(topic, payload=payload, qos=2)
        print(".", end="", flush=True)

    client.loop_stop()
    client.disconnect()
    elapsed = time.time() - t0
    print(f"\nDone. Replayed {len(events)} events in {elapsed:.1f}s")


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else LOG_PATH
    speed = float(sys.argv[2]) if len(sys.argv) > 2 else SPEED_FACTOR
    main(path, speed)
