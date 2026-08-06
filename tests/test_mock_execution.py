import pytest
from unittest.mock import patch
from alpss.alpss_main import alpss_main
import matplotlib.pyplot as plt


def test_alpss_main_success(valid_inputs):
    with patch("alpss.utils.phases.spall_doi_finder") as mock_spall_doi_finder, patch(
        "alpss.utils.phases.carrier_frequency"
    ) as mock_carrier_frequency, patch(
        "alpss.utils.phases.carrier_filter"
    ) as mock_carrier_filter, patch(
        "alpss.utils.phases.velocity_calculation"
    ) as mock_velocity_calculation, patch(
        "alpss.utils.phases.instantaneous_uncertainty_analysis"
    ) as mock_iua, patch(
        "alpss.utils.phases.velocity_uncertainty_analysis"
    ) as mock_vu, patch(
        "alpss.utils.phases.spall_analysis"
    ) as mock_spall_analysis, patch(
        "alpss.utils.phases.spall_uncertainty_analysis"
    ) as mock_sua, patch(
        "alpss.utils.phases.plot_results"
    ) as mock_plotting, patch(
        "alpss.utils.phases.save"
    ) as mock_saving:

        # Set up return values for velocity phase
        mock_spall_doi_finder.return_value = {"t_doi_start": 0.0, "t_doi_end": 1.0}
        mock_carrier_frequency.return_value = 2e9
        mock_carrier_filter.return_value = {}
        mock_velocity_calculation.return_value = {
            "time_f": [0, 1],
            "velocity_f": [100, 200],
            "velocity_f_smooth": [100, 200],
            "v_max_comp": 200,
            "t_max_comp": 0.5,
        }
        mock_iua.return_value = {"vel_uncert": [1, 2], "tau": 1e-9}
        mock_vu.return_value = {
            "peak_velocity_freq_uncert": 1e6,
            "peak_velocity_vel_uncert": 5,
            "peak_velocity_idx": 1,
        }

        # Set up return values for analysis phases
        mock_spall_analysis.return_value = {
            "v_max_ten": 150,
            "t_max_ten": 0.6,
            "v_rc": 180,
            "t_rc": 0.7,
            "spall_strength_est": 1e9,
            "strain_rate_est": 1e6,
            "max_ten_freq_uncert": 1e6,
            "max_ten_vel_uncert": 5,
        }
        mock_sua.return_value = {
            "spall_uncert": 1e8,
            "strain_rate_uncert": 1e5,
        }

        mock_plotting.return_value = plt.Figure()
        mock_saving.return_value = dict()

        result = alpss_main(**valid_inputs)

        assert isinstance(result[0], plt.Figure)
        assert isinstance(result[1], dict)

        mock_spall_doi_finder.assert_called_once()
        mock_carrier_frequency.assert_called_once()
        mock_carrier_filter.assert_called_once()
        mock_velocity_calculation.assert_called_once()
        mock_iua.assert_called_once()
        mock_vu.assert_called_once()
        mock_spall_analysis.assert_called_once()
        mock_sua.assert_called_once()
        mock_plotting.assert_called_once()
        mock_saving.assert_called_once()
