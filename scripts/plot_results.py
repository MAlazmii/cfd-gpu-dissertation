"""Validate the curated records and render both dissertation figures."""
import csv
import json
import math
from pathlib import Path
from statistics import linear_regression, mean, stdev

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
BACKENDS = ("openmp", "hip")
SCALES = (36, 72, 144, 216, 288, 360, 576)
ITERATIONS = (500, 1000, 2000, 5000, 10000)
BLOCK_X = (256, 128, 64, 32, 16, 8, 4, 2, 1)
INK, MUTED, BACKGROUND, PANEL = "#edf4f3", "#adbfcc", "#101b26", "#162836"
STYLES = {"openmp": ("OpenMP target", "#ffc581", "s"), "hip": ("Native HIP", "#64dfc8", "o")}


def grouped(name, group_columns, value_column, expected_groups, repeats):
    groups = {}
    with (ROOT / "data" / name).open(newline="") as file:
        for row in csv.DictReader(file):
            group = tuple(row[key] for key in group_columns)
            repeat = int(row["repeat"])
            value = float(row[value_column])
            runs = groups.setdefault(group, {})
            if repeat in runs or value <= 0 or not math.isfinite(value):
                raise ValueError(f"Invalid timing for {group} repeat {repeat}")
            if name == "mi210-timings.csv":
                if int(row["grid_side"]) != 32 * int(row["scale"]) or int(row["iterations"]) != 5000:
                    raise ValueError("Unexpected main comparison workload")
                total = float(row["total_seconds"])
                if not math.isclose(value * 5000, total, rel_tol=1e-5):
                    raise ValueError("Total and per-iteration timings disagree")
            runs[repeat] = value
    if set(groups) != set(expected_groups) or any(
        set(runs) != set(range(1, repeats + 1)) for runs in groups.values()
    ):
        raise ValueError(f"Incomplete experiment: {name}")
    return {key: [runs[i] for i in range(1, repeats + 1)] for key, runs in groups.items()}


def figure(title, subtitle, notes):
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 6.25), facecolor=BACKGROUND)
    fig.subplots_adjust(left=.084, right=.958, bottom=.234, top=.72, wspace=.30)
    fig.text(.084, .895, title, color=INK, fontsize=27, weight="bold")
    fig.text(.084, .833, subtitle, color=MUTED, fontsize=12)
    for axis in axes:
        axis.set_facecolor(PANEL)
        axis.spines[:].set_visible(False)
        axis.tick_params(colors=MUTED, length=0, pad=6)
        axis.grid(axis="y", color=MUTED, alpha=.2)
        axis.set_axisbelow(True)
    for y, line in zip((.117, .073), notes):
        fig.text(.084, y, line, color=MUTED, fontsize=9.5)
    return fig, axes


def label(axis, title, x, y):
    axis.set_title(title, loc="left", color=INK, fontsize=13, weight="bold", pad=13)
    axis.set_xlabel(x, color=MUTED)
    axis.set_ylabel(y, color=MUTED)


def legend(axis):
    axis.legend(facecolor=PANEL, edgecolor="#34505f", labelcolor=INK, framealpha=1)


def save(fig, name):
    path = ROOT / "figures" / name
    path.parent.mkdir(exist_ok=True)
    fig.savefig(path, dpi=175, facecolor=BACKGROUND, metadata={"Software": "CFD GPU dissertation case study"})
    plt.close(fig)


def main_comparison(timings, experiment):
    fig, (runtime, bandwidth) = figure(
        "GPU stencil performance on AMD MI210",
        "ARCHER2 · 7 grid sizes · 5,000 iterations · 5 sequential repeats per implementation and size",
        (
            "Means and one sample standard deviation are shown. Triad comes from a separate measured run.",
            "Effective bandwidth uses 32 B per interior point per iteration, divided by time per iteration.",
        ),
    )
    sizes = [32 * scale for scale in SCALES]
    reference = experiment["project_stream_triad_gb_s"]
    bytes_per_point = experiment["model_bytes_per_point_iteration"]
    for key in BACKENDS:
        name, color, marker = STYLES[key]
        samples = [timings[key, str(scale)] for scale in SCALES]
        times = [mean(values) * 1e6 for values in samples]
        errors = [stdev(values) * 1e6 for values in samples]
        runtime.errorbar(sizes, times, yerr=errors, capsize=3, color=color, marker=marker, label=name)
        percentages = [
            100 * bytes_per_point * side**2 / mean(values) / 1e9 / reference
            for side, values in zip(sizes, samples)
        ]
        bandwidth.plot(sizes, percentages, color=color, marker=marker, label=name)
    for axis in (runtime, bandwidth):
        axis.set_xscale("log", base=2)
        axis.set_xticks([sizes[i] for i in (0, 1, 2, 4, 6)], [f"{sizes[i]:,}" for i in (0, 1, 2, 4, 6)])
    runtime.set_yscale("log")
    bandwidth.set_ylim(0, 112)
    bandwidth.axhline(100, color=MUTED, linestyle="--", linewidth=1, label="Measured Triad reference")
    label(runtime, "Time per iteration", "Interior grid side (points, log scale)", "Solver time (µs, log scale)")
    label(bandwidth, "Effective bandwidth relative to Triad", "Interior grid side (points, log scale)", "Share of 1,312.1 GB/s (%)")
    legend(runtime)
    legend(bandwidth)
    save(fig, "mi210-comparison.png")


def diagnostics(sweep, blocks):
    fig, (cost, shape) = figure(
        "What changed the runtime?",
        "Separate ARCHER2 diagnostics · iteration count at 1,152² and HIP block shape at 9,216²",
        (
            "Each point shows the mean of three runs; whiskers show one sample standard deviation. The dashed lines are linear fits.",
            "Block shapes all use 256 threads. The 512-thread production configuration is outside this comparison.",
        ),
    )
    for key in BACKENDS:
        name, color, marker = STYLES[key]
        samples = [sweep[key, str(n)] for n in ITERATIONS]
        means = [mean(values) for values in samples]
        fit = linear_regression(ITERATIONS, means)
        cost.errorbar(ITERATIONS, means, yerr=[stdev(values) for values in samples], color=color,
                      fmt=marker, capsize=3, label=f"{name} · {fit.slope * 1e6:.1f} µs/iter")
        cost.plot([0, ITERATIONS[-1]], [fit.intercept, fit.intercept + fit.slope * ITERATIONS[-1]],
                  color=color, linestyle="--", alpha=.8)
    cost.set_xticks([0, 2000, 5000, 10000], ["0", "2,000", "5,000", "10,000"])
    means = [mean(blocks[str(x), str(256 // x)]) for x in BLOCK_X]
    baseline = min(means)
    shape.errorbar(range(len(BLOCK_X)), [v / baseline for v in means],
                   yerr=[stdev(blocks[str(x), str(256 // x)]) / baseline for x in BLOCK_X],
                   color=STYLES["hip"][1], marker="o", capsize=3)
    shape.axhline(1, color=MUTED, linestyle="--", linewidth=1)
    shape.set_yscale("log")
    shape.set_yticks([1, 2, 4, 8, 16], ["1×", "2×", "4×", "8×", "16×"])
    shape.set_xticks(range(len(BLOCK_X)), [str(x) for x in BLOCK_X])
    label(cost, "Iteration count and total solver time", "Iterations", "Timed region (seconds)")
    label(shape, "Narrow blocks were slower", "Contiguous threads per block (BLOCK_X)", "Runtime / fastest shape (log scale)")
    legend(cost)
    save(fig, "mi210-diagnostics.png")


def main():
    plt.rcdefaults()
    plt.rcParams["font.family"] = "DejaVu Sans"
    exp = json.loads((ROOT / "data/experiment.json").read_text())
    timings = grouped("mi210-timings.csv", ("implementation", "scale"), "seconds_per_iteration",
                      [(key, str(s)) for key in BACKENDS for s in SCALES], 5)
    sweep = grouped("mi210-iteration-sweep.csv", ("implementation", "iterations"), "total_seconds",
                    [(key, str(n)) for key in BACKENDS for n in ITERATIONS], 3)
    blocks = grouped("mi210-block-shapes.csv", ("block_x", "block_y"), "seconds_per_iteration",
                     [(str(x), str(256 // x)) for x in BLOCK_X], 3)
    main_comparison(timings, exp)
    diagnostics(sweep, blocks)


if __name__ == "__main__":
    main()
