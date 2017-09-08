# coding: utf-8

# Standard library
import os
from os import path

# Third-party
import h5py
import numpy as np
import gala.integrate as gi
import gala.coordinates as gc
import gala.dynamics as gd
from gala.dynamics.util import estimate_dt_n_steps
from superfreq import SuperFreq

# Project
from .config import ConfigNamespace, ConfigItem
from .log import logger

__all__ = ['FreqMap']

class Config(ConfigNamespace):
    energy_tolerance = ConfigItem(
        1E-8, "Maximum allowed fractional energy difference")

    n_periods = ConfigItem(
        256, "Total number of orbital periods to integrate for")

    n_steps_per_period = ConfigItem(
        512, "Number of steps per integration period (determines step size)")

    hamming_p = ConfigItem(
        4, "Exponent to use for Hamming filter in SuperFreq")

    n_intvec = ConfigItem(
        12, "Maximum number of integer vectors to use in SuperFreq")

    force_cartesian = ConfigItem(
        False, "Do frequency analysis on orbit in cartesian coordinates")


class FreqMap(object):
    cache_dtype = [
        ('freqs', 'f8', (2,3)), # three fundamental frequencies computed in 2 windows
        ('amps', 'f8', (2,3)), # amplitudes of frequencies in time series
        ('dE_max', 'f8'), # maximum energy difference (compared to initial) during orbit integration
        ('success', 'b1'), # did we succeed in computing the frequencies
        ('is_tube', 'b1'), # the orbit is a tube orbit
        ('dt', 'f8'), # timestep used for integration
        ('nsteps', 'i8'), # number of steps integrated
        ('error_code', 'i8') # if not successful, why did it fail? see below
    ]

    def __init__(self, cache_file, config_file=None, overwrite=False):

        # Name of this experiment
        self.name = self.__class__.__name__.lower()

        # Validate the cache path
        self.cache_file = path.abspath(cache_file)
        if not path.exists(self.cache_file):
            raise IOError("Cache file at '{0}' doesn't exist! You must first "
                          "generate a cache file with the loaded grid of "
                          "initial conditions.".format(self.cache_file))

        # Load the configuraton settings for this experiment
        config = Config()
        if config_file is not None:
            config.load(config_file)
        self.config = config

        # Load initial conditions
        with h5py.File(self.cache_file) as f:
            self.w0 = gd.PhaseSpacePosition.from_hdf5(f['w0'])

        self.norbits = len(self.w0)
        logger.info("Number of orbits: {0}".format(self.norbits))

    @classmethod
    def run(cls, w0, potential, **kwargs):
        c = dict()
        for k in cls.config_defaults.keys():
            if k not in kwargs:
                c[k] = cls.config_defaults[k]
            else:
                c[k] = kwargs[k]

        # return dict
        result = dict()

        # get timestep and nsteps for integration
        try:
            dt, nsteps = estimate_dt_nsteps(w0.copy(), potential,
                                            c['nperiods'],
                                            c['nsteps_per_period'])
        except RuntimeError:
            logger.warning("Failed to integrate orbit when estimating dt,nsteps")
            result['freqs'] = np.ones((2,3))*np.nan
            result['success'] = False
            result['error_code'] = 1
            return result
        except:
            logger.warning("Unexpected failure!")
            result['freqs'] = np.ones((2,3))*np.nan
            result['success'] = False
            result['error_code'] = 4
            return result

        # integrate orbit
        logger.debug("Integrating orbit with dt={0}, nsteps={1}".format(dt, nsteps))
        try:
            t,ws = potential.integrate_orbit(w0.copy(), dt=dt, nsteps=nsteps,
                                             Integrator=gi.DOPRI853Integrator,
                                             Integrator_kwargs=dict(atol=1E-11))
        except RuntimeError: # ODE integration failed
            logger.warning("Orbit integration failed.")
            dEmax = 1E10
        else:
            logger.debug('Orbit integrated successfully, checking energy conservation...')

            # check energy conservation for the orbit
            E = potential.total_energy(ws[:,0,:3].copy(), ws[:,0,3:].copy())
            dE = np.abs(E[1:] - E[0])
            dEmax = dE.max() / np.abs(E[0])
            logger.debug('max(∆E) = {0:.2e}'.format(dEmax))

        if dEmax > c['energy_tolerance']:
            logger.warning("Failed due to energy conservation check.")
            result['freqs'] = np.ones((2,3))*np.nan
            result['success'] = False
            result['error_code'] = 2
            result['dE_max'] = dEmax
            return result

        # start finding the frequencies -- do first half then second half
        sf1 = SuperFreq(t[:nsteps//2+1], p=c['hamming_p'])
        sf2 = SuperFreq(t[nsteps//2:], p=c['hamming_p'])

        # classify orbit full orbit
        circ = gd.classify_orbit(ws)
        is_tube = np.any(circ)

        # define slices for first and second parts
        sl1 = slice(None,nsteps//2+1)
        sl2 = slice(nsteps//2,None)

        if is_tube and not c['force_cartesian']:
            # first need to flip coordinates so that circulation is around z axis
            new_ws = gd.align_circulation_with_z(ws, circ)
            new_ws = gc.cartesian_to_poincare_polar(new_ws)
            fs1 = [(new_ws[sl1,j] + 1j*new_ws[sl1,j+3]) for j in range(3)]
            fs2 = [(new_ws[sl2,j] + 1j*new_ws[sl2,j+3]) for j in range(3)]

        else:  # box
            fs1 = [(ws[sl1,0,j] + 1j*ws[sl1,0,j+3]) for j in range(3)]
            fs2 = [(ws[sl2,0,j] + 1j*ws[sl2,0,j+3]) for j in range(3)]

        logger.debug("Running SuperFreq on the orbits")
        try:
            freqs1,d1,ixs1 = sf1.find_fundamental_frequencies(fs1, nintvec=c['nintvec'])
            freqs2,d2,ixs2 = sf2.find_fundamental_frequencies(fs2, nintvec=c['nintvec'])
        except:
            result['freqs'] = np.ones((2,3))*np.nan
            result['success'] = False
            result['error_code'] = 3
            return result

        result['freqs'] = np.vstack((freqs1, freqs2))
        result['dE_max'] = dEmax
        result['is_tube'] = float(is_tube)
        result['dt'] = float(dt)
        result['nsteps'] = nsteps
        result['amps'] = np.vstack((d1['|A|'][ixs1], d2['|A|'][ixs2]))
        result['success'] = True
        result['error_code'] = 0
        return result
