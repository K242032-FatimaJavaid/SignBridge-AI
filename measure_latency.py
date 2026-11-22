from pathlib import Path
import csv
import time
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Create the folder where evaluation results will be saved
out = Path("evaluation")
out.mkdir(exist_ok=True)

# List the workflows that will be tested
tasks = [
    ("ASL to Speech", "Begin signing -> speech starts"),
    ("Speech to Avatar", "Begin speaking -> avatar starts"),
    ("Gemini Assistant", "Click Send -> reply appears")
]

# Store the timing results
records = []

print("Measure each workflow using the running application.")
print("Press Enter when starting and when you see the result.")

# Test each workflow
for name, explanation in tasks:
    print("\n", name, ":", explanation)

    # Run three trials for each workflow
    for trial in range(1, 4):
        input(f"Trial {trial}: Press Enter as you START...")

        # Start the timer
        start = time.perf_counter()

        input("Press Enter when the result STARTS...")

        # Calculate how much time has passed
        elapsed = time.perf_counter() - start

        # Save the result
        records.append((name, trial, round(elapsed, 3)))
        print(f"{elapsed:.3f} seconds")

# Save all timing results into a CSV file
with open(out / "latency_results.csv", "w", newline="") as f:
    writer = csv.writer(f)

    # Write the column names
    writer.writerow(["Module", "Trial", "Seconds"])

    # Write all recorded results
    writer.writerows(records)

# Get the names of the tested modules
names = [t[0] for t in tasks]

# Calculate the average response time for each module
means = [
    statistics.mean(r[2] for r in records if r[0] == n)
    for n in names
]

# Create a bar chart for the average response times
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(names, means)

# Show the average time above each bar
ax.bar_label(bars, fmt="%.2f s", padding=4)

# Add labels and title to the chart
ax.set_ylabel("Mean Observed Response Time (Seconds)")
ax.set_title("SignBridge AI: Response Time Comparison")

# Set the maximum value of the y-axis
ax.set_ylim(0, max(means) * 1.2 + 0.1)

# Adjust the chart layout
fig.tight_layout()

# Save the chart as an image
fig.savefig(out / "03_response_time.png", dpi=200)

# Close the chart
plt.close(fig)

print("Saved evaluation/03_response_time.png")
print("Note: human-timed measurements are approximate.")
