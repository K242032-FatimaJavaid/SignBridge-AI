from pathlib import Path
import csv
import time
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

out = Path("evaluation")
out.mkdir(exist_ok=True)

tasks = [
    ("ASL to Speech", "Begin signing -> speech starts"),
    ("Speech to Avatar", "Begin speaking -> avatar starts"),
    ("Gemini Assistant", "Click Send -> reply appears")
]

records = []

print("Measure each workflow using the running application.")
print("Press Enter when starting and when you see the result.")

for name, explanation in tasks:
    print("\n", name, ":", explanation)
    for trial in range(1, 4):
        input(f"Trial {trial}: Press Enter as you START...")
        start = time.perf_counter()
        input("Press Enter when the result STARTS...")
        elapsed = time.perf_counter() - start
        records.append((name, trial, round(elapsed, 3)))
        print(f"{elapsed:.3f} seconds")

with open(out / "latency_results.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Module", "Trial", "Seconds"])
    writer.writerows(records)

names = [t[0] for t in tasks]
means = [
    statistics.mean(r[2] for r in records if r[0] == n)
    for n in names
]

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(names, means)
ax.bar_label(bars, fmt="%.2f s", padding=4)
ax.set_ylabel("Mean Observed Response Time (Seconds)")
ax.set_title("SignBridge AI: Response Time Comparison")
ax.set_ylim(0, max(means) * 1.2 + 0.1)
fig.tight_layout()
fig.savefig(out / "03_response_time.png", dpi=200)
plt.close(fig)

print("Saved evaluation/03_response_time.png")
print("Note: human-timed measurements are approximate.")
