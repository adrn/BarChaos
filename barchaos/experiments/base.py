# coding: utf-8

# Standard library
from abc import ABCMeta, abstractproperty
from abc import abstractclassmethod
from os import path
import os
import pickle

# Third-party
import h5py
import numpy as np
import gala.dynamics as gd

# Project
from ..log import logger
from ..potential import get_hamiltonian
from .error import error_codes

__all__ = ['Experiment']

class Experiment(object):

    __metaclass__ = ABCMeta

    @abstractproperty
    def cache_dtype(self):
        """ The numpy dtype of the dataset written to the cache file """

    @abstractproperty
    def config(self):
        """ A ConfigNamespace subclass instance containing config defaults """

    def __init__(self, cache_file, config_file=None, overwrite=False):

        # Name of this experiment
        self.name = self.__class__.__name__.lower()

        # Validate the cache path
        self.cache_file = path.abspath(cache_file)
        if not path.exists(self.cache_file):
            raise IOError("Cache file at '{0}' doesn't exist! You must first "
                          "generate a cache file with the loaded grid of "
                          "initial conditions.".format(self.cache_file))
        self._cache_path = path.dirname(self.cache_file)

        # Load the configuraton settings for this experiment
        self.config_file = config_file
        self.config.load(self.config_file)

        # Load initial conditions
        with h5py.File(self.cache_file) as f:
            self.w0 = gd.PhaseSpacePosition.from_hdf5(f['w0'])

        self.n_orbits = self.w0.shape[0]
        logger.info("Number of orbits: {0}".format(self.n_orbits))

        self.overwrite = overwrite

        # Now we initialize the cache file so it has an empty dataset to be
        # filled by this experiment
        self._init_cache()

    @property
    def _dtype(self):
        # all experiments must also return an error code - see error.py
        return self.cache_dtype + [('error_code', 'i8')]

    def _init_cache(self):
        with h5py.File(self.cache_file) as f:
            if self.name not in f:
                # create the empty dataset
                f.create_dataset(name=self.name,
                                 dtype=self._dtype,
                                 shape=(self.n_orbits,))

    @property
    def _empty_result(self):
        """ Get an empty result array to load into the HDF5 cache file """
        arr = []
        for obj in self._dtype:
            name = obj[0]
            dt = obj[1]

            if len(obj) > 2:
                shape = obj[2]
            else:
                shape = ()

            if name == 'error_code': # special-case this one
                val = 0

            elif 'b' in dt:
                val = False

            elif 'f' in dt:
                val = np.full(shape, np.nan, dtype=dt)

            elif 'i' in dt:
                val = np.full(shape, 0, dtype=dt)

            elif 's' in dt.lower():
                val = ""

            else:
                raise ValueError("Unknown")

            arr.append(val)

        return np.array([tuple(arr)], dtype=self._dtype)

    # These methods enable the class to be used as a context manager. When used
    # in this mode, the class creates a temporary directory to write all of the
    # intermediate results to, and cleans them up at the end.
    def __enter__(self):
        self._tmpdir = path.join(self._cache_path,
                                 "_tmp_{0}".format(self.__class__.__name__))

        logger.debug("Creating temp. directory {0}".format(self._tmpdir))
        if path.exists(self._tmpdir):
            import shutil
            shutil.rmtree(self._tmpdir)
        os.mkdir(self._tmpdir)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if path.exists(self._tmpdir):
            logger.debug("Removing temp. directory {0}".format(self._tmpdir))
            import shutil
            shutil.rmtree(self._tmpdir)
            self._tmpdir = None

    # The functions that actually do the running:

    @abstractclassmethod
    def run(cls, w0, potential, **kwargs):
        """ (classmethod) Run the experiment on a single orbit """

    def callback(self, tmpfile):
        """A function that operates on the name of the temporary cache file that
        each worker writes. This function should run on the master process, and
        will take the returned file and write it to the correct row in the cache
        file. The temp. cache file is a pickle containing results from a single
        worker, i.e. for a single orbit.
        """

        if tmpfile is None: # orbit already done
            return

        # Load the results from the
        with open(tmpfile,'rb') as f:
            index, result = pickle.load(f)
        os.remove(tmpfile) # remove the file as soon as we load it

        logger.debug("Writing orbit {0} results to cache file..."
                     .format(index))

        # row index
        with h5py.File(self.cache_file, 'a') as f:
            g = f[self.name]
            g[index] = result

        del result

    def __call__(self, index):
        logger.info("Orbit {0}".format(index))

        # Read the results for just this orbit
        with h5py.File(self.cache_file, 'r') as f:
            g = f[self.name]
            error_code = g[index]['error_code']

        # Short-circuit if this orbit is already done
        if not self.overwrite and error_code > 0:
            logger.debug("Orbit {0} already completed.".format(index))
            return None

        # Load the Hamiltonian object to use to integrate orbits
        H = get_hamiltonian(self.config_file)

        # Only pass in things specified in _run_kwargs (w0 and potential required)
        # kwargs = dict([(k,self.config[k])
        #                for k in self.config.keys() if k in self._run_kwargs])
        res = self.run(w0=self.w0[index], H=H)

        if res['error_code'] > 1:
            logger.warning(error_codes[res['error_code'][0]])

        # cache res into a tempfile, return name of tempfile
        tmpfile = path.join(self._tmpdir, "{0}-{1}.pickle".format(self.__class__.__name__, index))
        with open(tmpfile, 'wb') as f:
            pickle.dump((index, res), f)
        return tmpfile

    def status(self):
        """
        Prints out (to the logger) the status of the current run of the experiment.
        """

        with h5py.File(self.cache_file) as f:
            d = f[self.name]

            # numbers
            nsuccess = d['success'].sum()
            nfail = ((d['success'] == False) & (d['error_code'] > 0)).sum()

            logger.info("------------- {0} Status -------------"
                        .format(self.name))
            logger.info("Total number of orbits: {0}".format(self.n_orbits))
            logger.info("Succeeded: {0}".format(nsuccess))
            logger.info("Failed: {0}".format(nfail))

            for ecode in sorted(error_codes.keys()):
                n = (d['error_code'] == ecode).sum()
                logger.info("\t({0}) {1}: {2}".format(ecode,
                                                      error_codes[ecode], n))
