from sys import version_info
from setuptools import setup


__name__ = "hf_futures"
__version__ = "1.0.9"

if version_info.major == 3 and version_info.minor < 6 or \
        version_info.major < 3:
    print("Your Python interpreter must be 3.8 or greater!")
    exit(1)

setup(
    name=__name__,
    version=__version__,
    description="Automated cryptocurrency trader built with Python.",
    packages=["bot"],
    scripts=["bin/bot"],
    install_requires=[
        "pandas",
        "ccxt==4.4.31",
        "setuptools==69.5.1",
        "pytoml==0.1.21",
        "cfscrape==1.9.5",
        "psutil",
        "pyinstaller==4.4",
        "scipy==1.10.1",
    ],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Topic :: Office/Business :: Financial :: Investment",
        "Intended Audience :: Science/Research"
    ]
)
