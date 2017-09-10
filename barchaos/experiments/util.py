import numpy as np

def orbit_to_poincare_polar(orbit):
    r"""
    Convert an array of 6D Cartesian positions to Poincaré
    symplectic polar coordinates. These are similar to cylindrical
    coordinates.

    Parameters
    ----------

    """

    if orbit.norbits > 1:
        raise RuntimeError("Can only use with one orbit.")

    R = np.sqrt(orbit.x.value**2 + orbit.y.value**2)
    phi = np.arctan2(orbit.x.value, orbit.y.value) # TODO: is this right?

    vR = ((orbit.x*orbit.v_x + orbit.y*orbit.v_y) / R).value
    Theta = (orbit.x*orbit.v_y - orbit.y*orbit.v_x).value

    # pg. 437, Papaphillipou & Laskar (1996)
    # http://articles.adsabs.harvard.edu/cgi-bin/nph-iarticle_query?1996A%26A...307..427P&amp;data_type=PDF_HIGH&amp;whole_paper=YES&amp;type=PRINTER&amp;filetype=.pdf
    sqrt_2THETA = np.sqrt(np.abs(2*Theta))

    fs = [R+1j*vR,
          sqrt_2THETA * (np.cos(phi) + 1j*np.sin(phi)),
          orbit.z.value+1j*orbit.v_z.value]

    return fs
