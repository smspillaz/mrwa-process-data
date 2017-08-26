# /setup.py
#
# Installation and setup script for Main Roads Data Processing
#
# See /LICENCE.md for Copyright information
"""Installation and setup script for Main Roads Data Processing."""

from setuptools import find_packages, setup

setup(name="main-roads-data-processor-cli",
      version="0.0.1",
      description="""Main Roads Data Processor.""",
      long_description=(
          """Command line interface to translate a main roads video """
          """into a package suitable for use with a darknet image detection """
          """model."""
      ),
      author="Sam Spilsbury, Thomas Favoury",
      author_email="smspillaz@gmail.com",
      classifiers=["Development Status :: 3 - Alpha",
                   "Programming Language :: Python :: 2",
                   "Programming Language :: Python :: 2.7",
                   "Programming Language :: Python :: 3",
                   "Programming Language :: Python :: 3.1",
                   "Programming Language :: Python :: 3.2",
                   "Programming Language :: Python :: 3.3",
                   "Programming Language :: Python :: 3.4",
                   "Intended Audience :: Developers",
                   "Topic :: Software Development :: Build Tools",
                   "License :: OSI Approved :: MIT License"],
      url="http://github.com/smspillaz/main-roads-data-processing",
      license="ISC",
      keywords="nlp",
      packages=find_packages(
          exclude=["build", "dist", "*.egg-info", "*node_modules*"]
      ),
      install_requires=[
          "setuptools"
      ],
      entry_points={
          "console_scripts": [
              "mrwa-data-process=mrwaprocess.main:main"
          ]
      },
      zip_safe=True,
      include_package_data=True)
