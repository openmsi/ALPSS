# Simulated-signal benchmark

Checks how accurate ALPSS is on signals where the right answer is known.

```
cases.py ──generate.py──> data/   synthetic signal + true velocity + expected results
data/    ──run.py───────> runs/<label>/   ALPSS outputs per case
runs/    ──summarize.py─> summary.md      error of each result vs. the truth
```

1. Each case in `cases.py` describes a shot (type, noise level, seed).
2. `generate.py` builds the velocity history, turns it into a noisy PDV signal,
   and works out the results ALPSS should report.
3. `run.py` runs ALPSS on every signal, using the config in
   `tests/input_data/config.json`.
4. `summarize.py` compares the outputs with the truth. With `--against`, it also
   compares two runs, for example `main` and your branch.

Run everything from the repo root.

```bash
poetry run python benchmarks/generate.py                       # once, or after editing cases
poetry run python benchmarks/run.py --label main               # ALPSS as currently checked out
poetry run python benchmarks/summarize.py benchmarks/runs/main
```

To evaluate a change, run the cases on each version under its own label and compare:

```bash
git switch main          && poetry run python benchmarks/run.py --label main
git switch my-feature    && poetry run python benchmarks/run.py --label my-feature
poetry run python benchmarks/summarize.py benchmarks/runs/my-feature --against benchmarks/runs/main
```

`--set key=value` on `run.py` overrides any config key for every case
(for example `--set smoothing_window=101`), and `--only case_02 case_03` limits
any step to some cases.

## Pieces

- `alpss.simulation.pdv_synthesis` (in the package) synthesizes the signals.
- `cases.py` holds the default profile and synthesis parameters and lists the
  cases: shot type, overrides of those defaults, noise level, seed, and the
  config switches the case needs (`spall_enabled`, `hel_enabled`).
- `truth.py` derives the expected ALPSS results from the profile parameters and
  the material constants in `tests/input_data/config.json`.
- `generate.py` writes `data/<case>.csv` (the signal), `data/<case>.velocity_true.csv`
  and `data/<case>.truth.json`. Noise is seeded, so the files are reproducible.
- `run.py` runs `alpss_main_with_config` on each case with
  `tests/input_data/config.json`, changing only what the signal dictates: file
  paths, `sample_rate`, `lam` (= the reference wavelength), the read window
  (whole file), the HEL window (the config's window, shifted to the shock
  arrival) and the case's enabled phases. Outputs go to `runs/<label>/<case>/`
  with a `run.json` recording the git state and overrides.
- `summarize.py` writes `summary.md` / `summary.csv` into the run directory.

`data/` and `runs/` are gitignored.

## Truth

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

Times are in ALPSS's time base, which starts at 0 at the first sample of the file.

## Summary columns

- `error` = measured − truth; `rel_error` = error / truth.
- `ok` is the OK flag of the phase that produced the value (Velocity, Spall or HEL).
- `uncertainty` is the uncertainty ALPSS reports for that value, where it reports one,
  and `covered` says whether `|error| ≤ uncertainty`.
- The velocity trace rows give the RMS and maximum error of the smoothed velocity
  against the true history, over the window ALPSS analysed.
- With `--against`, each value is marked better / worse / same depending on which
  run is closer to the truth (relative error, or absolute where the truth is 0).
