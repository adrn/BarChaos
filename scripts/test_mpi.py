from os import path
import sys

# Third-party
import astropy.units as u
import gala.dynamics as gd
import numpy as np
import h5py
import schwimmbad

# Package
from barchaos.experiments.freqmap import FreqMap
from barchaos.log import logger

logger.setLevel(1)

def cache_file():
    fn = path.join('/tmp/cache.hdf5')

    w0 = gd.PhaseSpacePosition(pos=np.random.random((3,16))*u.kpc,
                               vel=np.random.random((3,16))*u.m/u.s)
    with h5py.File(fn, 'w') as f:
        g = f.create_group('w0')
        w0.to_hdf5(g)

    return fn

def test_freqmap_mpi(cache_file, pool):

    with FreqMap(cache_file) as exp:
        pool.map(exp, list(range(16)), callback=exp.callback)

    exp.status()

if __name__ == '__main__':
    pool = schwimmbad.MPIPool()
    if not pool.is_master():
        pool.wait()
        sys.exit(0)

    test_freqmap_mpi(cache_file(), pool)

    pool.close()
