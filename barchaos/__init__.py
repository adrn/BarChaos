__version__ = '0.1'

try:
    __BARCHAOS_SETUP__
except NameError:
    __BARCHAOS_SETUP__ = False

if not __BARCHAOS_SETUP__:
    __all__ = ['experiments', 'potential']

    from . import experiments, potential
