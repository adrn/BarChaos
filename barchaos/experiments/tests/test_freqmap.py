# Third-party
import astropy.units as u
import pytest
import gala.dynamics as gd
import numpy as np
import h5py
import schwimmbad

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
        tmpfile = exp(0)
        exp.callback(tmpfile)

        exp.status()

def test_freqmap_multi(cache_file):

    with FreqMap(cache_file) as exp:
        with schwimmbad.MultiPool() as pool:
            pool.map(exp, list(range(16)), callback=exp.callback)

        exp.status()

