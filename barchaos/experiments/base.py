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
from .log import logger
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
        if config_file is not None:
            self.config.load(config_file)

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




    def callback(self, tmpfile):
        """
        TODO:
        """

        if tmpfile is None:
            logger.debug("Tempfile is None")
            return

        with open(tmpfile,'rb') as f:
            result = pickle.load(f)
        os.remove(tmpfile)

        logger.debug("Flushing {0} to output array...".format(result['index']))
        memmap = np.memmap(self.cache_file, mode='r+',
                           dtype=self.cache_dtype, shape=(len(self.w0),))
        if result['error_code'] != 0.:
            logger.error("Error code = {0}".format(result['error_code']))
            # error happened
            for key in memmap.dtype.names:
                if key in result:
                    memmap[key][result['index']] = result[key]

        else:
            # all is well
            for key in memmap.dtype.names:
                memmap[key][result['index']] = result[key]

        # flush to output array
        memmap.flush()
        logger.debug("...flushed, washing hands.")

        del result
        del memmap

    def __call__(self, index):
        logger.info("Orbit {0}".format(index))

        # unpack input argument dictionary
        import gary.potential as gp
        potential = gp.load(path.join(self.cache_path, self.config.potential_filename))

        # read out just this initial condition
        norbits = len(self.w0)
        allfreqs = np.memmap(self.cache_file, mode='r',
                             shape=(norbits,), dtype=self.cache_dtype)

        # short-circuit if this orbit is already done
        if allfreqs['success'][index]:
            logger.debug("Orbit {0} already successfully completed.".format(index))
            return None

        # Only pass in things specified in _run_kwargs (w0 and potential required)
        kwargs = dict([(k,self.config[k]) for k in self.config.keys() if k in self._run_kwargs])
        res = self.run(w0=self.w0[index], potential=potential, **kwargs)
        res['index'] = index

        # cache res into a tempfile, return name of tempfile
        tmpfile = path.join(self._tmpdir, "{0}-{1}.pickle".format(self.__class__.__name__, index))
        with open(tmpfile, 'wb') as f:
            pickle.dump(res, f)
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

    @abstractclassmethod
    def run(cls, w0, potential, **kwargs):
        """ (classmethod) Run the experiment on a single orbit """
