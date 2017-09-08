
from ..freqmap import FreqMap
from ...log import logger

logger.setLevel(1)

def test_freqmap():
    exp = FreqMap('/Users/adrian/projects/barchaos/tmp/cache.hdf5')

    with FreqMap('/Users/adrian/projects/barchaos/tmp/cache.hdf5') as exp:
        exp.status()
        print(exp._empty_result)
