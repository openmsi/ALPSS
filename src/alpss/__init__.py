# Backward-compatible re-exports (pre-1.4.0 flat layout)
from alpss.detection.spall_doi_finder import spall_doi_finder
from alpss.carrier.frequency import carrier_frequency
from alpss.carrier.filter import carrier_filter
from alpss.velocity.calculation import velocity_calculation
from alpss.analysis.spall import spall_analysis
from alpss.analysis.full_uncertainty import full_uncertainty_analysis
from alpss.analysis.instantaneous_uncertainty import instantaneous_uncertainty_analysis
from alpss.plotting.plots import plot_results, plot_voltage
from alpss.io.saving import save
from alpss.utils import extract_data, stft
