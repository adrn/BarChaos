# Third-party
import schwimmbad

# Project
from barchaos import experiments
from barchaos.log import logger

if __name__ == "__main__":
    from argparse import ArgumentParser
    import logging

    # Define parser object
    parser = ArgumentParser(description="")

    vq_group = parser.add_mutually_exclusive_group()
    vq_group.add_argument('-v', '--verbose', action='count', default=0,
                          dest='verbosity')
    vq_group.add_argument('-q', '--quiet', action='count', default=0,
                          dest='quietness')

    parser.add_argument('-o', '--overwrite', action='store_true',
                        dest='overwrite', default=False,
                        help='Destroy everything.')

    # For schwimmbad / pool selection
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--ncores', dest='n_cores', default=1,
                       type=int, help='Number of processes (uses '
                                      'multiprocessing).')
    group.add_argument('--mpi', dest='mpi', default=False,
                       action='store_true', help='Run with MPI.')

    # For this script
    parser.add_argument('-e', '--experiment', dest='experiment', required=True,
                        type=str, help='The name of the experiment class to '
                                       'execute.')
    parser.add_argument('--cache', dest='cache_file', required=True,
                        type=str, help='Path to the cache file.')
    parser.add_argument('--config', dest='config_file', default=None,
                        type=str, help='Path to a configuration file.')

    args = parser.parse_args()

    # Set logger level based on verbose flags
    if args.verbosity != 0:
        if args.verbosity == 1:
            logger.setLevel(logging.DEBUG)
        else: # anything >= 2
            logger.setLevel(1)

    elif args.quietness != 0:
        if args.quietness == 1:
            logger.setLevel(logging.WARNING)
        else: # anything >= 2
            logger.setLevel(logging.ERROR)

    else: # default
        logger.setLevel(logging.INFO)

    pool = schwimmbad.choose_pool(mpi=args.mpi, processes=args.n_cores)

    cls = getattr(experiments, args.experiment)

    with cls(cache_file=args.cache_file, config_file=args.config_file,
             overwrite=args.overwrite) as exp:

        for _ in pool.map(exp, list(range(exp.n_orbits)),
                          callback=exp.callback):
            pass

        exp.status()

    pool.close()
