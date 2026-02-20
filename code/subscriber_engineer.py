# subscriber_engineer.py
# ----------------------------------------------------------





# ----------------------------------------------------------

import json
import time
import statistics
import csv
import paho.mqtt.client as mqtt

from policy import decrypt_fields

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "dt/test"

latencies = []
count = 0
window_start = time.time()


last_alg = "UNKNOWN"


LOG_FILE = "perf_log.csv"


def init_log_file():
    """如果 CSV 不存在，写入表头。"""
    try:
        with open(LOG_FILE, "x", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "mode", "msgs_per_sec",
                             "p50_ms", "p95_ms"])
    except FileExistsError:
        pass


def on_message(client, userdata, message):
    global latencies, count, window_start, last_alg

    now = time.time()
    try:
        payload = message.payload.decode("utf-8")
        data = json.loads(payload)


        hdr = data.get("_enc_header", {})
        alg = hdr.get("alg", "NONE")
        last_alg = alg


        data = decrypt_fields(data)


        if "timestamp" in data:
            try:
                latencies.append(now - float(data["timestamp"]))
            except (ValueError, TypeError):
                pass

        enc_fields = hdr.get("enc_fields", [])
        print(f"[ENGINEER] enc_fields={enc_fields} | data={data}")

        count += 1

    except Exception as e:
        print("[ENGINEER] parse error:", e)


def print_stats():
    global latencies, count, window_start, last_alg

    now = time.time()
    elapsed = now - window_start

    if elapsed >= 10 and count > 0:
        try:
            p50 = statistics.median(latencies)
        except statistics.StatisticsError:
            p50 = 0.0

        if len(latencies) >= 20:
            try:
                p95 = statistics.quantiles(latencies, n=20)[18]
            except Exception:
                p95 = p50
        else:
            p95 = p50

        thr = count / elapsed

        mode = "crypto_on" if last_alg == "AES-256-GCM" else "crypto_off"

        print("\n[ENGINEER] --- 10s stats ---")
        print(f"  mode         : {mode}")
        print(f"  messages/sec : {thr:.2f}")
        print(f"  p50 latency  : {p50*1000:.2f} ms")
        print(f"  p95 latency  : {p95*1000:.2f} ms")
        print("----------------------------\n")


        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
                mode,
                f"{thr:.2f}",
                f"{p50*1000:.3f}",
                f"{p95*1000:.3f}",
            ])

        latencies.clear()
        count = 0
        window_start = now


def main():
    init_log_file()

    client = mqtt.Client(client_id=f"eng-{int(time.time())}")
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=30)
    client.subscribe(TOPIC, qos=0)
    client.loop_start()

    try:
        while True:
            time.sleep(1)
            print_stats()
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
