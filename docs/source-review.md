# Saved implementation review

The dissertation studies the irrotational-flow configuration of a
two-dimensional solver. Each interior point takes the average of its four
neighbors from the previous iterate. Both GPU paths then copy the interior
temporary field back. Fixed boundary cells are preserved. The update error
is computed on the final iteration before copy-back and normalized by the
initial field norm.

| Implementation | Memory management | Work sharing |
| --- | --- | --- |
| OpenMP target | One enclosing target-data region maps the two fields across iterations | Separate directives perform the stencil, copy-back and final diagnostic reduction |
| Native HIP | Explicit device allocation and host-to-device and device-to-host copies | Separate launches implement the stencil, copy-back and final diagnostic reduction |

The native HIP launch maps adjacent X lanes to adjacent columns. The port
retains the separate copy-back pass, which avoids introducing a pointer-swap
algorithm into the programming-model comparison. Its error reduction groups
floating-point additions differently from the directive implementation.

## Local host validation

The verification rebuilt temporary copies of the saved C serial and OpenMP
target implementations on an Apple M1. The OpenMP run used two threads
with target offload disabled. The verification replaced the post-timer
plot output with a dump of every double-precision grid entry, including
the boundary. The independent reference applies the boundary setup and
Jacobi updates using array slices.

The four cases used scale 1 for 1 and 17 iterations and scale 2 for 17 and
100 iterations. Both saved C paths matched the complete reference grids
exactly in these cases. This check exercises the host computation and the
output grid shape. The native HIP evidence remains the archived scalar
checks and timing logs.

## Scope

The drivers use fixed problem and boundary conventions. Their command-line
parsing does not provide production input validation. The saved HIP
diagnostic reduction assumes a power-of-two number of threads per block.
The measured production shape has 512 threads and every block-shape
configuration in the chart has 256.

This branch contains the case study, derived numerical records and plotting
code. The underlying university code, scheduler configurations and full
submitted report are held in the original archive. The study's reviewed
source snapshot and the producing source of a historical timing are distinct
pieces of evidence.
