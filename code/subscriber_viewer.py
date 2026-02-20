# subscriber_viewer.py
# ----------------------------------------------------------

# ----------------------------------------------------------

import json
import time
import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "dt/test"


SAFE_FIELDS = {"timestamp", "temperature", "pressure", "speed"}


def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode("utf-8"))
        view = {k: data.get(k) for k in SAFE_FIELDS}
        print(f"[VIEWER] {view}")
    except Exception as e:
        print("[VIEWER] parse error:", e)


def main():
    client = mqtt.Client(client_id=f"viewer-{int(time.time())}")
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=30)
    client.subscribe(TOPIC, qos=0)
    client.loop_forever()


if __name__ == "__main__":
    main()
