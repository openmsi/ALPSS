# ALPSS: Automated Analysis of PDV Spall Signals

**ALPSS** (A naL ysis of P hotonic Doppler velocimetry S ignals of S pall) automates the analysis of PDV traces generated in laser shock experiments.

---

## Scientific Background

ALPSS processes PDV voltage signals through several key steps:

1. **Spall Domain of Interest (DOI) finding**  
   - *Manual selection*: user-defined  
   - *Otsu algorithm*: variance-based thresholding  
   - *CUSUM algorithm*: detects abrupt changes using cumulative sums  

2. **Carrier frequency analysis**  
   - Determines dominant oscillations in the signal  

3. **Carrier filtering**  
   - *Gaussian notch*: removes carrier band in the frequency domain  
   - *Sin-fit subtract*: fits sinusoid and subtracts it from the trace  

4. **Velocity calculation**  
   - Converts filtered PDV signal to particle velocity  

5. **Uncertainty quantification**  
   - Point-by-point instantaneous uncertainty  
   - Spall strength and strain-rate uncertainty propagation  

---

## Software Usage

ALPSS is distributed as a **Python package** and **Docker container**. It can be run in multiple ways:

### 📦 Installation

```bash
pip install alpss
```

or pull the container:

```bash
docker pull openmsi/alpss:latest
```

once install, to run the code, you can use a CLI entrypoint that comes with the package/docker image:

```bash
alpss path/to/config.json
```

Or run from python:

```bash
from alpss import alpss_main

config = {
    "out_files_dir": "output_data/",
    "start_time_user": "otsu",
    "carrier_filter_type": "gaussian_notch",
    "save_data": "yes",
    "display_plots": "no"
    # ... other parameters ...
}

fig, items = alpss_main(**config)

```

⚙️ Example Config File

Outputs

- Figures: processed PDV traces and spall annotations
- Data files: velocity, uncertainty, and derived quantities
- Logs: full runtime and step-by-step diagnostics