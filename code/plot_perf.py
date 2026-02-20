# plot_perf.py
# ----------------------------------------------------------


# ----------------------------------------------------------

import csv
from collections import defaultdict
import matplotlib.pyplot as plt

LOG_FILE = "perf_log.csv"

def load_data():
    by_mode = defaultdict(list)  # mode -> list of (p50,p95)

    with open(LOG_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mode = row["mode"]
            p50 = float(row["p50_ms"])
            p95 = float(row["p95_ms"])
            by_mode[mode].append((p50, p95))


    summary = {}
    for mode, vals in by_mode.items():
        if not vals:
            continue
        p50_avg = sum(v[0] for v in vals) / len(vals)
        p95_avg = sum(v[1] for v in vals) / len(vals)
        summary[mode] = (p50_avg, p95_avg)
    return summary

def main():
    summary = load_data()
    if not summary:
        print("No data in perf_log.csv yet.")
        return

    modes = ["crypto_off", "crypto_on"]
    p50_vals = [summary[m][0] if m in summary else 0 for m in modes]
    p95_vals = [summary[m][1] if m in summary else 0 for m in modes]

    x = range(len(modes))
    width = 0.35

    plt.figure()
    plt.bar([i - width/2 for i in x], p50_vals, width, label="p50 latency")
    plt.bar([i + width/2 for i in x], p95_vals, width, label="p95 latency")

    plt.xticks(x, modes)
    plt.ylabel("Latency (ms)")
    plt.title("Field-Sensitive AES-GCM Overhead")
    plt.legend()
    plt.tight_layout()
    plt.savefig("perf_comparison.png", dpi=200)
    plt.show()

if __name__ == "__main__":
    main()
