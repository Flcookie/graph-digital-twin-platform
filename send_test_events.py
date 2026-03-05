import json
import time
import paho.mqtt.client as mqtt

client = mqtt.Client()

client.connect("localhost", 1883)

events = [
    {
        "timestamp": 1,
        "station_id": "S1",
        "part_id": "P1",
        "part_type": "part",
        "activity": "START"
    },
    {
        "timestamp": 2,
        "station_id": "S2",
        "part_id": "P1",
        "part_type": "part",
        "activity": "PROCESS"
    },
    {
        "timestamp": 3,
        "station_id": "S3",
        "part_id": "P1",
        "part_type": "part",
        "activity": "END"
    }
]

for e in events:

    client.publish(
        "component_event/test/all",
        json.dumps(e)
    )

    time.sleep(1)

print("Events sent")