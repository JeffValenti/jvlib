from math import exp, log, sqrt
from statistics import mean

from numpy import append, geomspace, linspace
from scipy.interpolate import splev, splrep


def get_wratio(wave, func=mean):
    """Calculate a wavelength ratio representative of input wavelengths.

    Parameters:
        wave - iterable of wavelengths or of iterables of wavelengths
        func - function to distill a list of wratio values, default=mean

    Returns:
        wratio - float, wavelength ratio
    """
    if isinstance(wave[0], (float, int)):
        wratio = [b/a for a, b in zip(wave[:-1], wave[1:])]
    else:
        wratio = []
        for w in wave:
            wratio.extend([b/a for a, b in zip(w[:-1], w[1:])])
    return func(wratio)


def make_geomwave(wmin, wmax, desired_wratio):
    """Make geometrically spaced wavelength bins (uniform step in log).

    Parameters:
        wmin - minimum wavelength for output bin centers
        wmax - maximum wavelength for output bin centers (same units as wmin)
        wratio_desired - target value for wave[i+1] / w[i]

    Returns:
        wgeom - wavelength bin centers (same units as wmin and wmax)
        wedge - wavelength bin edges (same units as wmin and wmax)
    """
    nwave = round(log(wmax / wmin) / log(desired_wratio))
    actual_wratio = exp(log(wmax / wmin) / nwave)
    halfwidth = sqrt(actual_wratio)
    wgeom = geomspace(wmin * halfwidth, wmax / halfwidth, num=nwave)
    wedge = append(wgeom / halfwidth, wgeom[-1] * halfwidth)
    return wgeom, wedge


def oversample_wave(wave, osamp):
    """Return wavelengths with osamp-1 new points between input points."""
    nin = len(wave)
    xin = linspace(0, nin-1, nin)
    nout = (nin - 1) * osamp + 1
    xout = linspace(0, nin-1, nout)
    bspline_param = splrep(xin, wave)
    return splev(xout, bspline_param)
