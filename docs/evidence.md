# Measurement and evidence notes

## Main GPU comparison

The figures reconstruct the principal AMD MI210 results from Chapter 6,
especially Table 6.1 of the submitted dissertation. The seven scale factors
are 36, 72, 144, 216, 288, 360 and 576. The interior side is 32 times the
scale factor. Every recorded production sample used 5,000 Jacobi iterations.

The OpenMP target series used Cray CCE 20.0.0. The native series used HIP
6.3.42134 with `gfx90a` and a 256 × 2 block. Both used one MI210 on
ARCHER2 with separate exclusive allocations. Each job ran a small,
untimed scale-4 warm-up before five sequential samples per size. The
OpenMP log also records a disabled-offload verification after the benchmark.
Neither the warm-ups nor the disabled-offload check enter the series.

[The timing CSV](../data/mi210-timings.csv) preserves all 70 production
records at their printed precision. Means and sample standard deviations
describe these within-job repeats. There is no estimate of variability
between independent allocations. The production logs do not record exact
Git commits. Their compiler and workload records can be checked, while
the exact historical source trees remain unverified.

Both timed regions include the initial and final field transfers and the
fixed iteration loop with a final update-error calculation. OpenMP enters
its target-data region inside the timer, including device allocation. The
HIP build allocates the device fields before the timer. Output file
writing follows the timed region. This allocation asymmetry matters when
interpreting the shorter runs.

## Bandwidth and profiler records

The comparison figure uses an effective bandwidth model of 32 bytes per
interior point per iteration. It divides that modeled traffic by the mean
solver time per iteration, then compares it to 1,312.1 GB/s from a separate project-written
MI210 STREAM Triad run. The reference is measured on this platform. The
model estimates effective throughput from the stencil's memory operations.
The profiler records below use hardware HBM counters.

[The profiler CSV](../data/mi210-profiler.csv) records separate duration and
HBM counter passes at scale 36 and 288. For each 100-iteration case, it
combines the stencil and copy-back dispatches and excludes the final error
reduction. At scale 288 the counters report approximately 31.95 HBM bytes
per interior point per iteration for both backends. The scale-36 data
reports lower traffic per point. This is consistent with memory hierarchy
effects, but the counter set does not establish their cause.

## Iteration and block-shape diagnostics

[The iteration sweep](../data/mi210-iteration-sweep.csv) holds scale at 36
and varies the number of iterations from 500 to 10,000. It includes 30
recorded samples. The chart fits a line to the mean of the three repeats
at each count. The slopes are about 130.7 µs per iteration for OpenMP and
40.9 µs for HIP. The fit intercepts are about 280 and 253 ms respectively.
An intercept aggregates fixed costs in the fitted model. The slope
includes main kernel and other recurring costs.

The recorded stencil and copy-back durations come from profiled
100-iteration cases. The slope comes from separate unprofiled runs.
Their difference is a cross-run diagnostic and cannot be assigned to
launch, synchronization or mapping individually.

[The block-shape sweep](../data/mi210-block-shapes.csv) includes 27
samples at scale 288. The nine shapes keep 256 threads per block and vary
the contiguous dimension from 256 to 1. The chart normalizes times to the
fastest measured shape, 128 × 2. The main comparison's 256 × 2 production
block contains 512 threads and is outside this sweep.

## Numerical evidence

[The scalar validation CSV](../data/scalar-validation.csv) records
serial, OpenMP target and HIP values at scales 36 and 288 after 100 and 500
iterations. All three implementations agree in the printed checksum and
normalized update error. The center probe printed zero for each case and
adds little discriminatory power. The archive contains scalar diagnostics
for these GPU runs. They cannot establish full-field or bitwise equality.

[The local host check](../data/local-host-validation.json) records the
fresh full-field comparison and its toolchain and source fingerprints.
[The experiment record](../data/experiment.json) records the archived log
fingerprints used to build the numeric tables.

## Acknowledgements

The serial and directive-based GPU implementations build on the EPCC
teaching baseline. The native HIP port and comparison were dissertation
work. [EPCC HPC Summer School CFD baseline](https://github.com/EPCCed/hpcss24-cfd)

The historical GPU experiments used the ARCHER2 UK National Supercomputing
Service. [Beckett et al. (2024), ARCHER2 Service Description](https://doi.org/10.5281/zenodo.14507040)
