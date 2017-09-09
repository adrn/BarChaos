# Third-party
import astropy.units as u
import pytest
import gala.dynamics as gd
import numpy as np
import h5py

# Package
from ..freqmap import FreqMap
from ...log import logger

logger.setLevel(1)

@pytest.fixture(scope='session')
def cache_file(tmpdir_factory):
    fn = tmpdir_factory.mktemp('cache').join('cache.hdf5')

    w0 = gd.PhaseSpacePosition(pos=np.random.random((3,16))*u.kpc,
                               vel=np.random.random((3,16))*u.m/u.s)
    with h5py.File(fn, 'w') as f:
        g = f.create_group('w0')
        w0.to_hdf5(g)

    return str(fn)

def test_freqmap(cache_file):
    exp = FreqMap(cache_file)

    with FreqMap(cache_file) as exp:
        exp.status()
        print(exp._empty_result)
