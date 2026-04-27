"""Shock stress calculations for spall/PDV analysis.

Two methods are provided:

* **Acoustic approximation** (simple):
    σ = 0.5 · ρ · C₀ · v_peak

* **Hugoniot EOS** (preferred, matches HELIX Toolbox):
    u_p      = v_fs / 2               (particle velocity from free-surface velocity)
    U_shock  = C₀ + S · u_p          (linear Hugoniot)
    σ        = ρ · U_shock · u_p

All functions return stress in **Pa**.  Divide by 1e9 for GPa.

The default S parameter per material is taken from the linear Hugoniot fits
listed in Meyers, "Dynamic Behavior of Materials" (1994) and Shock Wave Database
(www.ihed.ras.ru/rusbank).
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Hugoniot slope parameter S  (U_s = C₀ + S·u_p)
# Keys are lower-case aliases; update as needed.
# ---------------------------------------------------------------------------
_HUGONIOT_S: dict[str, float] = {
    # Copper
    "cu": 1.49, "copper": 1.49,
    # Aluminium
    "al": 1.34, "aluminum": 1.34, "aluminium": 1.34,
    # Zinc
    "zn": 1.30, "zinc": 1.30,
    # Brass (70Cu–30Zn typical)
    "brass": 1.43,
    # Titanium (CP-Ti / Grade 2)
    "ti": 1.02, "cp-ti": 1.02, "ti_grade2": 1.02, "ti grade2": 1.02,
    # Ti-6Al-4V
    "ti64": 1.05, "ti-6al-4v": 1.05, "ti6al4v": 1.05,
    # Vanadium
    "v": 1.22, "vanadium": 1.22,
    # Magnesium
    "mg": 1.54, "magnesium": 1.54,
}

_DEFAULT_S = 1.49  # fall back to Cu value when material not recognised


def get_hugoniot_S(material: str, default: float = _DEFAULT_S) -> float:
    """Return the Hugoniot slope parameter *S* for *material*.

    Parameters
    ----------
    material:
        Material name or abbreviation (case-insensitive).
    default:
        Value to return when the material is not in the built-in table.

    Returns
    -------
    float
        Hugoniot *S* parameter (dimensionless).
    """
    return _HUGONIOT_S.get(str(material).lower().strip(), default)


# ---------------------------------------------------------------------------
# Core stress calculations
# ---------------------------------------------------------------------------

def shock_stress_acoustic(density: float, C0: float, peak_velocity: float) -> float:
    """Acoustic approximation for peak shock stress.

    Parameters
    ----------
    density:
        Initial material density  [kg/m³].
    C0:
        Bulk wave speed  [m/s].
    peak_velocity:
        Free-surface velocity at peak  [m/s].

    Returns
    -------
    float
        Shock stress  [Pa].

    Notes
    -----
    σ = 0.5 · ρ · C₀ · v_peak
    This is the formula used in the original ALPSS code.
    """
    return 0.5 * density * C0 * float(peak_velocity)


def shock_stress_hugoniot(
    density: float,
    C0: float,
    peak_velocity: float,
    S: float = _DEFAULT_S,
) -> float:
    """Hugoniot EOS peak shock stress.

    Parameters
    ----------
    density:
        Initial material density  [kg/m³].
    C0:
        Bulk wave speed  [m/s].
    peak_velocity:
        Free-surface velocity at peak  [m/s].
    S:
        Hugoniot slope parameter (dimensionless).  Defaults to 1.49 (Cu).

    Returns
    -------
    float
        Shock stress  [Pa].

    Notes
    -----
    u_p     = v_fs / 2         (particle velocity)
    U_shock = C₀ + S·u_p      (shock velocity)
    σ       = ρ · U_shock · u_p
    """
    u_p = float(peak_velocity) / 2.0
    U_s = C0 + S * u_p
    return density * U_s * u_p


def shock_stress_hugoniot_uncertainty(
    density: float,
    C0: float,
    peak_velocity: float,
    peak_velocity_unc: float,
    S: float = _DEFAULT_S,
) -> float:
    """Propagated uncertainty for the Hugoniot shock stress.

    Uses first-order error propagation through
    ``σ = ρ · (C₀ + S·u_p) · u_p``  w.r.t. *u_p*.

    Parameters
    ----------
    density:
        Initial material density  [kg/m³].
    C0:
        Bulk wave speed  [m/s].
    peak_velocity:
        Free-surface velocity at peak  [m/s].
    peak_velocity_unc:
        1-σ uncertainty on *peak_velocity*  [m/s].
    S:
        Hugoniot slope parameter (dimensionless).

    Returns
    -------
    float
        1-σ shock stress uncertainty  [Pa].

    Notes
    -----
    δσ/δu_p = ρ · (C₀ + 2·S·u_p)
    δσ      = ρ · (C₀ + 2·S·u_p) · δu_p
    """
    u_p = float(peak_velocity) / 2.0
    u_p_unc = float(peak_velocity_unc) / 2.0
    return density * (C0 + 2.0 * S * u_p) * u_p_unc


def calculate_shock_stress(
    density: float,
    C0: float,
    peak_velocity: float,
    peak_velocity_unc: float = 0.0,
    material: str = "",
    S: float | None = None,
    method: str = "hugoniot",
) -> dict[str, float]:
    """Compute peak shock stress and its uncertainty.

    This is the primary entry point used by ``alpss_main`` and ``saving``.

    Parameters
    ----------
    density:
        Initial material density  [kg/m³].
    C0:
        Bulk wave speed  [m/s].
    peak_velocity:
        Free-surface velocity at peak  [m/s].
    peak_velocity_unc:
        1-σ uncertainty on *peak_velocity*  [m/s].
    material:
        Material name (used to look up *S* when *S* is ``None``).
    S:
        Hugoniot slope parameter.  If ``None`` the value is looked up from
        *material*; if the material is unknown the Cu default (1.49) is used.
    method:
        ``"hugoniot"`` (default) uses the EOS formula; ``"acoustic"`` uses
        the simple approximation.

    Returns
    -------
    dict with keys
        * ``"shock_stress_pa"``     – stress in Pa
        * ``"shock_stress_gpa"``    – stress in GPa
        * ``"shock_stress_unc_pa"`` – 1-σ uncertainty in Pa
        * ``"shock_stress_unc_gpa"``– 1-σ uncertainty in GPa
        * ``"method"``              – which formula was used
        * ``"S"``                   – Hugoniot *S* value used (nan for acoustic)
    """
    if S is None:
        S_val = get_hugoniot_S(material) if material else _DEFAULT_S
    else:
        S_val = float(S)

    if method == "acoustic":
        stress_pa = shock_stress_acoustic(density, C0, peak_velocity)
        unc_pa = shock_stress_acoustic(density, C0, peak_velocity_unc) if peak_velocity_unc else 0.0
        S_used = np.nan
    else:
        stress_pa = shock_stress_hugoniot(density, C0, peak_velocity, S_val)
        unc_pa = shock_stress_hugoniot_uncertainty(density, C0, peak_velocity, peak_velocity_unc, S_val)
        S_used = S_val

    return {
        "shock_stress_pa": stress_pa,
        "shock_stress_gpa": stress_pa * 1e-9,
        "shock_stress_unc_pa": unc_pa,
        "shock_stress_unc_gpa": unc_pa * 1e-9,
        "method": method,
        "S": S_used,
    }
