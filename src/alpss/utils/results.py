from dataclasses import dataclass, field
import numpy as np


@dataclass
class HELResult:
    """Result of Hugoniot Elastic Limit detection."""

    ok: bool
    strength_gpa: float = np.nan
    uncertainty_gpa: float = np.nan
    free_surface_velocity: float = np.nan
    time_detection_ns: float = np.nan
    consecutive_points: int = 0
    segment_duration_ns: float = np.nan
    strain_rate: float = np.nan
    error_message: str | None = None
    # Internal data for plotting (gradient method)
    segment_start_idx: int | None = None
    segment_end_idx: int | None = None
    time_window: np.ndarray | None = None
    velocity_window: np.ndarray | None = None
    gradient_smooth: np.ndarray | None = None
    angles_deg: np.ndarray | None = None
    # Extra fields populated by the RDP + Linear Hybrid method
    method: str = "unknown"
    rise_slope: float = np.nan
    plateau_slope: float = np.nan
    rdp_knee_time_ns: float = np.nan
    rdp_points: np.ndarray | None = None
