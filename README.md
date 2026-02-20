# Field-Sensitive Adaptive Encryption (FSAE) for IIoT Digital Twin Telemetry

This mini project implements **Field-Sensitive Adaptive Encryption (FSAE)**: a context-aware, **field-level** encryption framework for Digital Twin telemetry streams. Instead of encrypting every message end-to-end, FSAE selectively encrypts only the **high-risk** (and sometimes medium-risk) fields to preserve **sub-millisecond latency** while protecting sensitive operational data. 

## Why this matters - Digital Twin systems rely on real-time telemetry for monitoring and control. Full-payload encryption can add overhead/jitter, while plaintext exposes sensitive information. FSAE balances both by encrypting only the fields that matter most. 
---

## Key ideas

### 1) S–I–T field scoring (Sensitivity–Impact–Timeliness)
Each telemetry field gets a score based on:
- **Sensitivity (S)**: confidentiality/privacy impact
- **Impact (I)**: operational/safety risk if modified
- **Timeliness (T)**: importance for real-time control

In the prototype, the score is computed as: `Score = 3S + 2I + T`, then mapped to **low / medium / high** risk.

### 2) Context-aware policy engine
Encryption decisions adapt at runtime using:
- **Network risk level** (LAN / WiFi / Public)
- **Subscriber role** (Engineer / Viewer / Admin)
- **Event state** (normal / alert)

Example behavior:
- In **alert**, encrypt **high + medium** fields.
- On **WiFi/Public**, encrypt **high**, and encrypt **medium** for non-viewer roles.
- On trusted **LAN** (normal), encrypt **high** only. 
### 3) Crypto mechanism: AES-256-GCM (per-field)
Selected fields are encrypted using **AES-256-GCM**, with a unique nonce per field per message (authenticated encryption).

---

## System architecture
A complete MQTT-based Digital Twin telemetry pipeline:
- **Publisher** generates JSON telemetry and selectively encrypts fields before publish
- **Mosquitto broker** routes messages
- **Engineer subscriber** decrypts and logs latency stats (p50/p95)
- **Viewer subscriber** shows only low-sensitivity fields (least-privilege)
- **Dashboard** visualizes telemetry + shows which fields are encrypted 

---

## Repository structure

### `policy.py`
Core FSAE logic:
- S–I–T scoring + field classification
- Context-aware `select_fields_to_encrypt(...)`
- `encrypt_fields(...)` with a switch to enable/disable real AES-GCM
- `decrypt_fields(...)` for subscribers 

### `publisher.py`
Simulated device/gateway publisher:
- Generates telemetry (timestamp, device_id, operator_id, temperature, pressure, speed)
- Rotates context (e.g., LAN <-> WiFi) to demonstrate adaptive policy
- Publishes at ~2 msg/s and prints payload size + encrypted fields 

### `subscriber_engineer.py`
Privileged subscriber:
- Decrypts encrypted fields
- Computes end-to-end latency and writes p50/p95 + throughput to `perf_log.csv` 

### `subscriber_viewer.py`
Restricted subscriber:
- Prints only a “safe view” of allowed low-sensitivity fields
- Ignores encrypted blobs (least-privilege behavior) 

### `dashboard.py`
Plotly Dash dashboard:
- Subscribes to MQTT stream
- Live plots (e.g., temperature/speed)
- Shows latest JSON + `_enc_header.enc_fields` 
### `plot_perf.py`
Reads `perf_log.csv` and plots crypto_on vs crypto_off latency comparison. 

---

## Setup (macOS)

### 1) Install Mosquitto (broker)
```bash
brew install mosquitto
brew services start mosquitto
```

### 2) Create a virtual environment + install Python deps
```
python3 -m venv .venv
source .venv/bin/activate
pip install paho-mqtt cryptography dash plotly matplotlib
```

## Run the demo

**Terminal 1 — Start publisher**
Edit ENABLE_CRYPTO inside publisher.py:
- False = baseline (no real encryption, only marks fields)
- True = FSAE enabled (AES-256-GCM on selected fields)

Run:
```
python3 publisher.py
```

**Terminal 2 — Engineer subscriber (decrypt + perf logs)**
```
python3 subscriber_engineer.py
```

**Terminal 3 — Viewer subscriber (safe fields only)**
```
python3 subscriber_viewer.py
```

**Terminal 4 — Dashboard (optional)**
```
python3 dashboard.py
```
Open the Dash URL it prints (typically http://127.0.0.1:8050).

- Plot results
After you have perf_log.csv:
```
python3 plot_perf.py
```
## What to expect
Your report’s evaluation compares crypto off vs crypto on while holding throughput constant at ~2 msg/s. It shows a small latency increase when FSAE is enabled while remaining below 1 ms end-to-end. 

~ Notes / security
- This repo uses a demo key inside policy.py. For a real system, load keys from secure storage and implement rotation. 
- Field-level encryption increases payload size because encrypted fields include nonce/tag/metadata (expected trade-off). 
