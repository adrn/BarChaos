# coding: utf-8

# Standard library
from os import path

# Third-party
import astropy.units as u
import biff.scf as bscf
import gala.potential as gp
from gala.units import galactic
import h5py
import numpy as np
from scipy.optimize import minimize

# Project
from ..log import logger
from ..config import ConfigNamespace, ConfigItem
from .bfe import get_scf_coeffs

__all__ = ['Config', 'get_hamiltonian']

class Config(ConfigNamespace):
    name = "potential"

    nmax = ConfigItem(6, "Maximum number of radial terms in the SCF expansion "
                         "of the bar component")
    lmax = ConfigItem(6, "Maximum number of spherical hamonic l terms")

    Omega = ConfigItem(40., "Bar pattern speed [km/s/kpc]")
    bar_mass = ConfigItem(1E10, "Bar mass [Msun]")

    # TODO: add other tunable parameters once I decide on the potential...

# ==============================================================================

# Define the potential model up to the bar component
potential_no_bar = gp.CCompositePotential()
potential_no_bar['disk'] = gp.MiyamotoNagaiPotential(m=5E10*u.Msun,
                                                     a=3*u.kpc,
                                                     b=280*u.pc,
                                                     units=galactic)
potential_no_bar['spheroid'] = gp.HernquistPotential(m=4E9*u.Msun,
                                                     c=0.6*u.kpc,
                                                     units=galactic)
potential_no_bar['halo'] = gp.NFWPotential(m=6E11, r_s=18*u.kpc,
                                           units=galactic)

def get_hamiltonian(config_file=None):
    c = Config()
    c.load(config_file)

    # TODO: this is just temporary...I need to decide on a better potential
    pot = gp.MilkyWayPotential()

    Om = [0., 0., c.Omega]*u.km/u.s/u.kpc
    frame = gp.ConstantRotatingFrame(Omega=Om, units=galactic)

    return gp.Hamiltonian(potential=pot, frame=frame)

def get_bar_potential(config_file=None):
    c = Config()
    c.load(config_file)

    # Generate a key to hash the expansion coefficients at in the coefficients
    # HDF5 file
    hash_key = str(hash((c.nmax, c.lmax, c.Omega)))
    fiducial_hash_key = str(hash((c.nmax, c.lmax, 0)))

    this_path = path.dirname(path.abspath(__file__))
    coeffs_filename = path.join(this_path, 'data', 'coeffs.hdf5')

    with h5py.File(coeffs_filename, 'a') as f:
        if hash_key in f:
            logger.debug("Loading cached expansion coefficients")
            return np.array(f[hash_key][:])

        elif fiducial_hash_key in f:
            fiducial_coeffs = np.array(f[fiducial_hash_key][:])

        else:
            fiducial_coeffs = None

    logger.info("Couldn't find cached expansion coefficients for nmax={0}, "
                "lmax={1}, Omega={2}. Computing now, but this could take some "
                "time...".format(c.nmax, c.lmax, c.Omega))

    if fiducial_coeffs is None:
        logger.debug("First computing coefficients for the fiducial model...")

        # First we need to get the fiducial model (no truncation) to determine
        # the corotation radius for any other model (ignore the Tnlm coeffs)
        fiducial_coeffs, _ = get_scf_coeffs(np.inf, c.nmax, c.lmax)

        with h5py.File(coeffs_filename, 'a') as f:
            d = f.create_dataset(name=fiducial_hash_key,
                                 data=fiducial_coeffs)
            d.attrs['Rmax'] = np.inf

    # Now that we have the fiducial model, we construct a potential object with
    # the un-truncated bar:
    pot = potential_no_bar.copy()
    fid_bar = bscf.SCFPotential(m=c.bar_mass, r_s=1.,
                                Snlm=fiducial_coeffs,
                                Tnlm=np.zeros_like(fiducial_coeffs),
                                units=galactic)
    pot['bar'] = fid_bar

    def func(R):
        vc = pot.circular_velocity([R,0,0.]).to(u.km/u.s).value
        return (vc - c.Omega * R)**2

    res = minimize(func, x0=5.)

    if not res.success:
        logger.warning('Failed to find corotation radius! Hopefully you '
                       'expected that...')
        return fid_bar

    Rmax = res.x[0]

    logger.debug("Now computing coefficients for the specific bar model...")
    coeffs, _ = get_scf_coeffs(Rmax, c.nmax, c.lmax)

    with h5py.File(coeffs_filename, 'a') as f:
        d = f.create_dataset(name=hash_key,
                             data=coeffs)
        d.attrs['Rmax'] = Rmax

    return bscf.SCFPotential(m=c.bar_mass, r_s=1.,
                             Snlm=coeffs,
                             Tnlm=np.zeros_like(fiducial_coeffs),
                             units=galactic)
