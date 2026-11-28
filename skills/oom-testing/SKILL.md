---
name: oom-testing
description: Estimate and measure scientific workload memory use, then test bounded failure and scaling behavior. Use when a workload may exhaust RAM or GPU memory, when scaling to larger datasets, or when sizing chunked or batched computations. This is out-of-memory testing, not order-of-magnitude sanity checking.
---

# OOM testing

Use when evaluating memory limits, larger datasets or workloads that may exhaust RAM or accelerator memory.

## Workflow

1. Identify the target platform and available memory, input sizes, dtypes and major allocations. Estimate bytes from shape and dtype, including copies, temporary arrays and quadratic pairwise operations. Record assumptions.
2. Choose a conservative resource budget. Run increasing small inputs in a child process with a timeout and a platform-appropriate memory cap when supported. Stop before exceeding the budget; never exhaust the user's machine to demonstrate failure. A timeout alone is not a memory cap.
3. Measure peak memory with a tool appropriate to the workload. Python allocation tracers omit many native or device allocations; OS high-water marks may use platform-dependent units. GPU tests need device-specific measurements and synchronization.
4. Compare observed growth with the estimate. If needed, use chunking, streaming, sparse representations or smaller batches while preserving numerical semantics.
5. Verify that the revised method matches an independently checked small result. Test invalid sizes and controlled allocation failure where practical. Report partial output policy and recovery behavior.

## Guardrails and completion

If safe caps or the target hardware are unavailable, report the estimate and leave stress testing unverified. Do not report performance or scalability beyond measured sizes. Distinguish memory testing from order-of-magnitude numerical sanity checks.

## Exercise

For an n-by-n float64 distance matrix, the output alone needs `8*n*n` bytes: at n=10,000 this is 800,000,000 bytes, excluding inputs and temporaries. Derive a row-chunk budget, then verify small chunked results before trying larger sizes. This is a worked sizing exercise, not a measured stress benchmark.
