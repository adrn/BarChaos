"""
Functions to help with determining the basis function expansion of the bar
density model.

See also my notebook with initial explorations: notebooks/Wang Zhao bar.ipynb
"""

# Standard library
import math

# Third-party
import biff.scf as bscf
import numpy as np

# ~ish from Dwek+1995
x0 = 1.75
y0 = 0.6
z0 = 0.4

__all__ = ['get_scf_coeffs']

def f(x, y, Rmax):
    R_2 = x**2 + y**2
    R0 = 0.5 # from Dwek+1995

    if R_2 < Rmax**2:
        return 1.

    else:
        return math.exp(-0.5 * R_2 / R0**2)

def dwek1995_G2_density(x, y, z, x0, y0, z0, Rmax):
    r1 = (((x/x0)**2 + (y/y0)**2)**2 + (z/z0)**4)**0.25
    return math.exp(-r1**2/2.) * f(x, y, Rmax)

def get_scf_coeffs(Rmax, nmax, lmax):
    """Given a truncation radius and expansion index truncations, compute the
    SCF coefficients for a given bar model.

    Parameters
    ----------
    Rmax : float [kpc]
        The cylindrical truncation (corotation) radius.
    nmax : int
        Maximum radial term index in the SCF expansion.
    lmax : int
        Maximum spherical term index in the SCF expansion.

    Returns
    -------
    Snlm : numpy.ndarray
    Tnlm : numpy.ndarray
    """
    args = (x0, y0, z0, Rmax)
    coeff = bscf.compute_coeffs(dwek1995_G2_density, nmax=nmax, lmax=lmax,
                                M=1., r_s=1., skip_odd=True, args=args)
    (S,Serr), (T,Terr) = coeff

    return S, np.zeros_like(S)
