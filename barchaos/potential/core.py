# coding: utf-8

# Standard library

# Third-party
import astropy.units as u
import gala.potential as gp
from gala.units import galactic

# Project
from .config import ConfigNamespace, ConfigItem

__all__ = ['Config', 'get_hamiltonian']

class Config(ConfigNamespace):
    name = "potential"

    Omega = ConfigItem(40., "Bar pattern speed [km/s/kpc]")
    # bar_mass = ConfigItem(0, "Bar mass [Msun]")

    # TODO: add other tunable parameters once I decide on the potential...

def get_hamiltonian(config_file=None):
    c = Config()
    c.load(config_file)

    # TODO: this is just temporary...I need to decide on a better potential
    pot = gp.MilkyWayPotential()

    Om = [0., 0., c.Omega]*u.km/u.s/u.kpc
    frame = gp.ConstantRotatingFrame(Omega=Om, units=galactic)

    return gp.Hamiltonian(potential=pot, frame=frame)
