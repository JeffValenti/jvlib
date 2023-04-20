# jvlib

Astronomy tools maintained by Jeff Valenti.
The code is not yet stable or documented.
Use at your own risk.

# Installation

Create a file named `jvlib.yml` with contents:

    name: jvlib
    channels:
      - default
      - astropy
    dependencies:
      - astropy
      - astroquery
      - ffmpeg
      - flake8
      - jupyter
      - matplotlib
      - numpy
      - pip
      - python=3.10
      - scipy
      - pip:
        - "git+https://github.com/JeffValenti/jvlib.git"

Create the `jvlib` conda environment, installing the jvlib package from the github repository.:

    conda env create -f jvlib.yml

To install the jvlib package in edit mode, clone the repository:

    git clone https://github.com/JeffValenti/jvlib.git

and replace the last line of jvlib.yml with:

        - -e /Users/valenti/python/jvlib

modifying the path to point at your local copy of the jvlib repository.

Activate the jvlib conda environment:

    conda activate jvlib
