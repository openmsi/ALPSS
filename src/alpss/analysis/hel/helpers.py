import numpy as np


def elastic_shock_strain_rate(C_L, U_hel, U_0, t_hel, t_0):
    """
    Compute elastic shock strain rate.

    Parameters
    ----------
    C_L : float
        Longitudinal wave velocity of the material (m/s).
    U_hel : float
        Free surface velocity at HEL (m/s).
    U_0 : float
        Free surface velocity at t=0 (m/s).
    t_hel : float
        Time at which U_hel is measured (s or ns — units must match t_0).
    t_0 : float
        Initial time (same units as t_hel).

    Returns
    -------
    float
        Elastic shock strain rate (1/s if times are in seconds, 1/ns if in ns).
    """
    dt = t_hel - t_0
    if dt <= 0:
        return np.nan
    return (1 / (2 * C_L)) * ((U_hel - U_0) / dt)


def _rdp_hel(points: np.ndarray, epsilon: float) -> np.ndarray:
    """RDP simplification returning kept indices (shared with spall module)."""
    if len(points) < 3:
        return np.arange(len(points))

    def _perp(pt, s, e):
        if np.allclose(s, e):
            return np.linalg.norm(pt - s)
        d = e - s
        proj = s + np.dot(pt - s, d) / np.dot(d, d) * d
        return np.linalg.norm(pt - proj)

    def _rec(pts, eps, off=0):
        if len(pts) < 3:
            return list(range(off, off + len(pts)))
        dists = [_perp(pts[i], pts[0], pts[-1]) for i in range(1, len(pts) - 1)]
        mx = max(dists)
        mi = dists.index(mx) + 1
        if mx > eps:
            L = _rec(pts[: mi + 1], eps, off)
            R = _rec(pts[mi:], eps, off + mi)
            return L[:-1] + R
        return [off, off + len(pts) - 1]

    return np.array(sorted(set(_rec(points, epsilon))))
