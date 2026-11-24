# ALPSS benchmark

Checks how accurate ALPSS is, with one config for every file
(`benchmark_config.json`, or any config you point it to). This is separate from
the tests: it reports errors, it doesn't pass or fail.

## Real files

The real files live in the Girder collection **ALPSS Benchmark Dataset**
(folder `real`), not in git. A case is a pair:

- `<id>.csv`: the scope trace
- `<id>-results.csv`: an ALPSS results file whose values are the reference

Every pair in `benchmarks/data/real/` is a case. To add a file, upload its pair
to the collection; nothing in the code changes. The summary compares Velocity
and Time at Max Compression, Carrier Frequency, Signal Start Time, Velocity and
Time at Max Tension, HEL Free Surface Velocity and HEL Time Detection, wherever
the results file has them (`cases.REFERENCE_METRICS`).

The references are not ground truth yet: the Lab files' are the lab pipeline's
results, and `example_file`'s are `main`'s (Otsu, whole file). They will be
replaced by results processed by hand.

**`benchmark.ipynb`** is the front end: set the config and a label, then run the
cells to fetch the missing pairs (needs `GIRDER_API_URL` / `GIRDER_API_KEY`),
run ALPSS on every file and show the per-metric stats, error histograms and the
worst files. The same steps from a shell, from `benchmarks/`:

```bash
poetry run python run.py --real --label my-branch [--config ...] [--set start_time_user=cusum]
poetry run python summarize.py runs/my-branch [--against runs/main]
```

`benchmark_config.json` is `tests/input_data/config.json` with the settings the
Lab files have been run with so far: whole record, `lam` = 1550 nm,
1.8–2.8 GHz, `t_before`/`t_after` = 25/100 ns, a 45 ns smoothing window and a
`[15, 5]` blur kernel. They were chosen for the start time: at 2.8 GHz the
band cuts the top of the velocity on these files, so the velocity results
(and what depends on them) come out low.

## Simulated files (twins)

```
cases.py ──generate.py──> data/   synthetic signal + true velocity + expected results
data/    ──run.py───────> runs/<label>/   ALPSS outputs per case
runs/    ──summarize.py─> summary.md      error of each result vs. the truth
```

1. Each case in `cases.py` is a twin of a real file in `data/real/`, with one
   ingredient changed (noise, Doppler amplitude, velocity).
2. `generate.py` measures the real file, rebuilds it with a known velocity using
   the original simulation code (`alpss.simulation.velocity_to_pdv_voltage`), and
   works out the results ALPSS should report.
3. `run.py` (without `--real`) runs ALPSS on every twin with the same config.
4. `summarize.py` compares the outputs with the truth. With `--against`, it also
   compares two runs, for example `main` and your branch.

The twins' truth covers the start time, carrier frequency and peak velocity only.

```bash
poetry run python benchmarks/generate.py                       # once, or after editing cases
poetry run python benchmarks/run.py --label main               # ALPSS as currently checked out
poetry run python benchmarks/summarize.py benchmarks/runs/main
```

To evaluate a change, run each version under its own label and compare:

```bash
git switch main          && poetry run python benchmarks/run.py --real --label main
git switch my-feature    && poetry run python benchmarks/run.py --real --label my-feature
poetry run python benchmarks/summarize.py benchmarks/runs/my-feature --against benchmarks/runs/main
```

`--set key=value` on `run.py` overrides any config key for every case
(for example `--set start_time_user=cusum`), and `--only case_02 case_03` limits
any step to some cases.

## Pieces

- `twins.py` measures a real file (carrier, carrier and Doppler amplitudes over
  time, velocity, shock arrival, noise) and passes it to
  `alpss.simulation.velocity_to_pdv_voltage`, unchanged. The velocity is zero
  before the arrival, so the twin's start time is exact. That code has constant
  light powers and white noise, so a twin keeps the real file's average
  proportions but not how they change over time (e.g. a carrier fade before the
  shock).
- `cases.py` lists the simulated cases (twins and their variants) and finds the
  real ones from the files (`real_cases()`).
- `truth.py` derives the expected ALPSS results from the profile parameters and
  the material constants in the config.
- `generate.py` writes `data/<case>.csv` (the signal), `data/<case>.velocity_true.csv`
  and `data/<case>.truth.json`. Noise is seeded, so the files are reproducible.
- `run.py` runs `alpss_main_with_config` on each case with the config. Real
  files run with it as is; for twins it changes only what the signal dictates:
  file paths, `lam` (= the reference wavelength), the read window (whole file),
  the HEL window (the config's window, shifted to the shock arrival) and the
  case's enabled phases. Outputs go to `runs/<label>/<case>/`
  with a `run.json` recording the git state and overrides.
- `summarize.py` writes `summary.md`, `summary.csv`, `stats.csv` and `errors.png`
  (a histogram of errors per metric) into the run directory.

`data/` and `runs/` are gitignored.

## Truth (twins)

| Result | Truth |
|---|---|
| Velocity at Max Compression | `V_peak`, the maximum of the true velocity history |
| Velocity at Max Tension | `V_plat − dV_spall` |
| Time at Max Tension | `t_spall` |
| Spall Strength | `0.5·ρ·C0·dV_spall` |
| Strain Rate | `0.5/C0 · dV_spall / (t_spall − t_plat_end)`, the true pullback slope (ALPSS measures from the time of peak velocity) |
| HEL Free Surface Velocity | `V_HEL` |
| HEL Strength (GPa) | `0.5·ρ·C_L·V_HEL` |
| Peak Shock Stress | `0.5·ρ·C0·V_peak` |
| Carrier Frequency | `c/λ_ref − c/λ_tar` |
| Signal Start Time | shock arrival, `−t_begin` |

For twins: Carrier Frequency, Signal Start Time (the measured arrival),
Velocity at Max Compression and Peak Shock Stress only.

Times are in ALPSS's time base, which starts at 0 at the first sample of the file.

## Summary columns

- `error` = measured − truth; `rel_error` = error / truth.
- The stats table comes first: per metric, `n` cases with a measured value and
  the `mean`, `std`, `mean_abs` and `max_abs` of their errors. Failed cases are
  left out of it.
- The velocity trace rows give the RMS and maximum error of the smoothed velocity
  against the true history, over the window ALPSS analysed.
- With `--against`, a comparison table lists each value's error in both runs.
