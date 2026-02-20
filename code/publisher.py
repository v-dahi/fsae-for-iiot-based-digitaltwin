# publisher.py
# -------------------------------------------------------------
# Digital Twin Data Publisher with S–I–T-based field selection
# and optional AES-GCM field-level encryption (switchable).
# -------------------------------------------------------------

import json
import time
import random
import paho.mqtt.client as mqtt

from policy import encrypt_fields

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "dt/test"




ENABLE_CRYPTO = True


def make_ctx(t: int) -> dict:
    """
    模拟上下文：
      - 每 20 条切换一次网络风险
      - event_state 默认 normal（你也可以改成 alert 测试策略变化）
    """
    return {
        "risk_level": "WiFi" if (t // 20) % 2 == 0 else "LAN",
        "role": "engineer",      # viewer / engineer / admin
        "event_state": "normal", # normal / alert
    }


def make_data() -> dict:
    """
    模拟物理端设备数据。
    """
    return {
        "timestamp": time.time(),
        "device_id": "machine-01",
        "operator_id": "op-1138",
        "temperature": round(25 + random.uniform(-1.0, 1.0), 2),
        "pressure": round(1.0 + random.uniform(-0.1, 0.1), 3),
        "speed": 1000 + random.randint(-50, 50),

        # "fault_code": 42 if random.random() < 0.1 else 0
    }


def main():
    client = mqtt.Client(client_id=f"pub-{int(time.time())}")
    client.connect(BROKER, PORT, keepalive=30)
    client.loop_start()

    t = 0
    try:
        while True:
            data = make_data()
            ctx  = make_ctx(t)


            processed = encrypt_fields(data, ctx, enable_crypto=ENABLE_CRYPTO)


            payload_str = json.dumps(processed)
            client.publish(TOPIC, payload_str, qos=0)


            raw_len = len(json.dumps(data))
            enc_len = len(payload_str)
            enc_fields = processed.get("_enc_header", {}).get("enc_fields", [])

            print(
                f"[PUB] crypto={ENABLE_CRYPTO} "
                f"raw={raw_len}B enc={enc_len}B "
                f"ctx={ctx} enc_fields={enc_fields}"
            )

            time.sleep(0.5)  # 2 messages per second
            t += 1

    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
