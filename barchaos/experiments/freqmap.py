# coding: utf-8

# Third-party
import numpy as np
import gala.integrate as gi
from gala.dynamics.util import estimate_dt_n_steps
from superfreq import SuperFreq

# Project
from ..config import ConfigNamespace, ConfigItem
from ..log import logger
from .base import Experiment
from .util import orbit_to_poincare_polar

__all__ = ['FreqMap']

class Config(ConfigNamespace):
    name = "freqmap"

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


class FreqMap(Experiment):
    # dtype of things output by this experiment
    cache_dtype = [
        ('freqs', 'f8', (2,3)), # three fundamental frequencies computed in 2 windows
        ('amps', 'f8', (2,3)), # amplitudes of frequencies in time series
        ('dE_max', 'f8'), # maximum energy difference (compared to initial) during orbit integration
        ('success', 'b1'), # did we succeed in computing the frequencies
        ('is_tube', 'b1'), # the orbit is a tube orbit
        ('dt', 'f8'), # timestep used for integration
        ('nsteps', 'i8') # number of steps integrated
    ]

    config = Config()

    # TODO: eek, this might be borked because I changed it from a classmethod...
    def run(self, w0, H):
        c = self.config

        # return dict
        result = self._empty_result

        # get timestep and nsteps for integration
        try:
            dt, nsteps = estimate_dt_n_steps(
                w0, H, n_periods=c.n_periods,
                n_steps_per_period=c.n_steps_per_period,
                func=np.nanmin, Integrator=gi.DOPRI853Integrator)
        except RuntimeError:
            result['error_code'] = 2
            return result
        except:
            result['error_code'] = 9
            return result

        # integrate orbit
        logger.debug("Integrating orbit with dt={0}, nsteps={1}".format(dt, nsteps))
        try:
            orbit = H.integrate_orbit(w0, dt=dt, n_steps=nsteps,
                                      Integrator=gi.DOPRI853Integrator,
                                      Integrator_kwargs=dict(atol=1E-11))
        except RuntimeError: # ODE integration failed
            logger.warning("Orbit integration failed.")
            dEmax = 1E10
        else:
            logger.debug('Orbit integrated successfully, checking energy conservation...')

            # check energy conservation for the orbit
            E = orbit.energy()
            dEmax = np.max(np.abs((E[1:] - E[0])/E[0]))
            logger.debug('max(∆E) = {0:.2e}'.format(dEmax))

        if dEmax > c.energy_tolerance:
            result['error_code'] = 4
            result['dE_max'] = dEmax
            return result

        # start finding the frequencies -- do first half then second half
        sf1 = SuperFreq(orbit.t[:nsteps//2+1].value, p=c.hamming_p)
        sf2 = SuperFreq(orbit.t[nsteps//2:].value, p=c.hamming_p)

        # classify orbit full orbit
        circ = orbit.circulation()
        is_tube = np.any(circ)

        # define slices for first and second parts
        sl1 = slice(None,nsteps//2+1)
        sl2 = slice(nsteps//2,None)

        if is_tube and not c.force_cartesian:
            # first need to flip coordinates so that circulation is around z axis
            new_orbit = orbit.align_circulation_with_z(circ)
            fs1 = orbit_to_poincare_polar(new_orbit[sl1])
            fs2 = orbit_to_poincare_polar(new_orbit[sl2])

        else:  # box
            ws = orbit.w()
            fs1 = [(ws[j,sl1] + 1j*ws[j+3,sl1]) for j in range(3)]
            fs2 = [(ws[j,sl2] + 1j*ws[j+3,sl2]) for j in range(3)]

        logger.debug("Running SuperFreq on the orbits")
        try:
            freqs1,d1,ixs1 = sf1.find_fundamental_frequencies(
                fs1, nintvec=c.n_intvec)
            freqs2,d2,ixs2 = sf2.find_fundamental_frequencies(
                fs2, nintvec=c.n_intvec)
        except:
            result['error_code'] = 5
            return result

        result['freqs'] = np.vstack((freqs1, freqs2))
        result['dE_max'] = dEmax
        result['is_tube'] = float(is_tube)
        result['dt'] = float(dt)
        result['nsteps'] = nsteps
        result['amps'] = np.vstack((d1['|A|'][ixs1], d2['|A|'][ixs2]))
        result['success'] = True
        result['error_code'] = 1
        return result
