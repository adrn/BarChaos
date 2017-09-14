#!/usr/bin/env python

import os
import sys
from setuptools import setup

# Hackishly inject a constant into builtins to enable importing of the
# package before the dependencies are installed.
if sys.version_info[0] < 3:
    import __builtin__ as builtins
else:
    import builtins
builtins.__BARCHAOS_SETUP__ = True
import barchaos

pkg_data = dict()
pkg_data["barchaos"] = ["README.md", "LICENSE"]
pkg_data["barchaos.potential"] = ["data/README.md",
                                  "data/coeffs.hdf5"]

setup(
    name="barchaos",
    version=barchaos.__version__,
    author="Adrian Price-Whelan",
    author_email="adrianmpw@gmail.com",
    url="https://github.com/adrn/BarChaos",
    packages=["barchaos", "barchaos.experiments", "barchaos.potential"],
    description="",
    long_description=open("README.md").read(),
    package_data=pkg_data,
    include_package_data=True,
    install_requires=["astropy", "numpy", "matplotlib"],
)
