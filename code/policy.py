# policy.py
"""
Field-Sensitive Adaptive Encryption (FSAE) with AES-256-GCM
and a switch to enable/disable real encryption.

- S–I–T scoring (Sensitivity, Impact, Timeliness)
- select_fields_to_encrypt: decide which fields to protect
- encrypt_fields(..., enable_crypto=True): 
      if True  -> real AES-GCM per-field
      if False -> just mark enc_fields, no encryption
- decrypt_fields: restore encrypted fields on subscriber side
"""

from typing import Dict, Any, Tuple, List
import json
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ========= Key config (demo) =========
KID = "kid-2025Q4-demo"
# 32-byte key (256 bits), DEMO ONLY. In real system load from secure storage.
MASTER_KEY = bytes.fromhex(
    "00112233445566778899aabbccddeeff"
    "00112233445566778899aabbccddeeff"
)
_AEAD = AESGCM(MASTER_KEY)

# ========= S–I–T config =========
FIELD_SIT: Dict[str, Dict[str, int]] = {
    "timestamp":   {"S": 0, "I": 1, "T": 3},
    "device_id":   {"S": 1, "I": 1, "T": 1},
    "operator_id": {"S": 3, "I": 2, "T": 1},
    "temperature": {"S": 1, "I": 1, "T": 3},
    "pressure":    {"S": 1, "I": 2, "T": 3},
    "speed":       {"S": 1, "I": 3, "T": 3},
    "fault_code":  {"S": 2, "I": 3, "T": 2},
    "geo_lat":     {"S": 3, "I": 2, "T": 2},
    "geo_lon":     {"S": 3, "I": 2, "T": 2},
}

def score_field(name: str) -> Tuple[int, str]:
    cfg = FIELD_SIT.get(name, {"S": 0, "I": 0, "T": 0})
    S, I, T = cfg["S"], cfg["I"], cfg["T"]
    total = 3 * S + 2 * I + 1 * T
    if total >= 8:
        level = "high"
    elif total >= 5:
        level = "medium"
    else:
        level = "low"
    return total, level

def classify_record(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for k in data.keys():
        score, level = score_field(k)
        result[k] = {"score": score, "level": level}
    return result

def select_fields_to_encrypt(
    data: Dict[str, Any],
    ctx: Dict[str, Any],
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Decide which fields should be encrypted based on S–I–T and context.
    Also apply simple masking rules (e.g., device_id).
    """
    info = classify_record(data)
    risk  = ctx.get("risk_level", "LAN")       # LAN / WiFi / Public / Unknown
    role  = ctx.get("role", "engineer")        # viewer / engineer / admin
    event = ctx.get("event_state", "normal")   # normal / alert

    enc: List[str] = []
    masked: List[str] = []

    # 1) Alert: encrypt high + medium level
    if event == "alert":
        for field, meta in info.items():
            if meta["level"] in ("high", "medium"):
                enc.append(field)

    # 2) High risk network: encrypt all high; medium for non-viewer
    elif risk in ("WiFi", "Public", "Unknown"):
        for field, meta in info.items():
            if meta["level"] == "high":
                enc.append(field)
            elif meta["level"] == "medium" and role != "viewer":
                enc.append(field)

    # 3) LAN + normal: encrypt only high
    else:  # LAN
        for field, meta in info.items():
            if meta["level"] == "high":
                enc.append(field)

    # 4) Mask device_id in higher risk or medium level
    if "device_id" in data:
        _, lvl = score_field("device_id")
        if lvl == "medium" or risk in ("WiFi", "Public", "Unknown"):
            masked.append("device_id")

    new_data = dict(data)
    if "device_id" in masked and isinstance(new_data.get("device_id"), str):
        v = new_data["device_id"]
        new_data["device_id"] = v[:-4] + "****" if len(v) > 4 else "****"

    enc = sorted(set(enc))
    return enc, new_data

# ========= AES-GCM helpers =========
def _encrypt_value(value: Any) -> Dict[str, Any]:
    pt = json.dumps(value).encode("utf-8")
    nonce = os.urandom(12)
    ct = _AEAD.encrypt(nonce, pt, None)
    return {
        "__enc__": True,
        "alg": "AES-256-GCM",
        "kid": KID,
        "nonce": nonce.hex(),
        "ct": ct.hex(),
    }

def _decrypt_value(box: Dict[str, Any]) -> Any:
    nonce = bytes.fromhex(box["nonce"])
    ct = bytes.fromhex(box["ct"])
    pt = _AEAD.decrypt(nonce, ct, None)
    return json.loads(pt.decode("utf-8"))

# ========= Public APIs =========
def encrypt_fields(
    data: Dict[str, Any],
    ctx: Dict[str, Any],
    enable_crypto: bool = True
) -> Dict[str, Any]:
    """
    Main entry for publisher:
      - If enable_crypto = False: only mark enc_fields, no AES-GCM.
      - If enable_crypto = True : AES-GCM encrypt selected fields.
    """
    enc_list, processed = select_fields_to_encrypt(data, ctx)
    out = dict(processed)

    header = {
        "policy": "SIT-v1",
        "kid": KID,
        "alg": "AES-256-GCM" if enable_crypto else "NONE",
        "risk_level": ctx.get("risk_level", "LAN"),
        "role": ctx.get("role", "engineer"),
        "event_state": ctx.get("event_state", "normal"),
        "enc_fields": [],
    }

    if not enable_crypto:
        # No real encryption, just record which fields WOULD be encrypted
        header["enc_fields"] = enc_list
        out["_enc_header"] = header
        return out

    # Real AES-GCM encryption
    for f in enc_list:
        if f not in out:
            continue
        out[f] = _encrypt_value(out[f])
        header["enc_fields"].append(f)

    out["_enc_header"] = header
    return out

def decrypt_fields(msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry for subscriber:
      - If alg != AES-256-GCM: do nothing (no encryption mode).
      - If alg == AES-256-GCM: decrypt all enc_fields.
    """
    if not isinstance(msg, dict):
        return msg

    out = dict(msg)
    hdr = out.get("_enc_header", {})
    alg = hdr.get("alg")

    if alg != "AES-256-GCM":
        # No encryption used, or unsupported algorithm
        return out

    kid = hdr.get("kid")
    if kid is not None and kid != KID:
        print(f"[WARN] unknown kid={kid}, skip decryption")
        return out

    for f in hdr.get("enc_fields", []):
        box = out.get(f)
        if isinstance(box, dict) and box.get("__enc__") and box.get("alg") == "AES-256-GCM":
            try:
                out[f] = _decrypt_value(box)
            except Exception as e:
                print(f"[ERROR] decrypt field {f} failed: {e}")

    return out
