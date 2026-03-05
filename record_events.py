import common
import datetime
import os
import paho.mqtt.client as mqtt
import pandas
from neo4j_writer import write_event_to_graph, close as neo4j_close

CONFIG = common.load_json("config.json")
LOG_FOLDER = CONFIG["log_folder"]
LOG_TIME = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
LOG_FILE = "event_log_" + LOG_TIME + ".csv"
LOG_PATH = os.path.join(LOG_FOLDER, LOG_FILE)
LOG_COLUMNS = CONFIG["log_columns"]
MQTT_BROKER_HOST = CONFIG["mqtt_broker_host"]
MQTT_BROKER_PORT = CONFIG["mqtt_broker_port"]


def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with code " + str(rc))
    topic = common.render_topic("component_event", "+", "all")
    client.subscribe(topic, qos=2)


def on_message(client, userdata, msg):
    context, source_id, target_id = common.parse_topic(msg.topic)
    payload = msg.payload.decode("utf-8")
    if context == "component_event":
        event = common.deserialize_object(payload)
        event_list.append(event)
        write_event_to_graph(event)


event_list = list()
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER_HOST, port=MQTT_BROKER_PORT)
mqtt_client.loop_start()

print("Start recording events")
try:
    while True:
        pass
except KeyboardInterrupt:
    print("Stop recording events")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

    # Save CSV backup
    event_log = pandas.DataFrame.from_records(event_list, columns=LOG_COLUMNS)
    event_log.sort_values(by="timestamp", inplace=True, kind="stable")
    os.makedirs(LOG_FOLDER, exist_ok=True)
    event_log.to_csv(LOG_PATH, index=False)
    print("Event log saved to " + LOG_PATH)

    # Close Neo4j connection
    neo4j_close()
    print("Neo4j connection closed")