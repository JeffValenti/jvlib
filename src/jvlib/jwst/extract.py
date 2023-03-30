from math import ceil, sqrt
from pathlib import Path

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from numpy import argwhere, diff, median, sum as np_sum
from scipy.ndimage import median_filter

from jvlib.util.obj import use_or_set_default


class SpectralExtraction:
    def __init__(self, image):
        self.image = image
        self.medfilt = (1, 5)
        self.peakfrac = 0.05
        self.madfact = 10
        self.filtim = None
        self.ysum = None
        self.thresh = None
        self.xlim = None

    def extract_spectrum(
            self, medfilt=None, peakfrac=None, madfact=None, thresh=None):
        """Execute spectral extraction steps in sequence."""
        medfilt = use_or_set_default(medfilt, self.medfilt)
        self.set_filtered_image(medfilt=medfilt)
        self.set_spatial_sum()
        peakfrac = use_or_set_default(peakfrac, self.peakfrac)
        madfact = use_or_set_default(madfact, self.madfact)
        self.set_spectral_limits(
            peakfrac=peakfrac, madfact=madfact, thresh=thresh)

    def set_filtered_image(self, filtim=None, medfilt=None):
        """Set the filtered image to default or to value provided by user."""
        if filtim:
            self.filtim = filtim
        else:
            medfilt = use_or_set_default(medfilt, self.medfilt)
            self.filtim = median_filter(
                self.image, size=medfilt, mode="nearest")

    def set_spatial_sum(self, spectrum=None):
        """Set the spatial sum to default or to spectrum provided by user."""
        if spectrum:
            self.ysum = spectrum
        else:
            self.ysum = np_sum(self.filtim, axis=0)

    def set_spectral_limits(
            self, limits=None, peakfrac=None, madfact=None, thresh=None):
        """Set spectral limits to default or to tuple provided by user."""
        if limits:
            self.xlim = limits
        else:
            peakfrac = use_or_set_default(peakfrac, self.peakfrac)
            madfact = use_or_set_default(madfact, self.madfact)
            peak = max(self.ysum)
            mad = median(abs(self.filtim))
            self.thresh = max(madfact * mad, peakfrac * peak)
            above_thresh = argwhere(self.ysum > self.thresh)
            self.xlim = (min(above_thresh)[0], max(above_thresh)[0])

    def plot_spectral_limits(self, figpath=None):
        if figpath is None:
            figpath = 'spectral_limits.pdf'
        xlo, xhi = self.xlim
        figure = Figure(figsize=(8, 8))
        axes = figure.subplots()
        axes.plot([0, len(self.ysum)], [0, 0], ls=':', lw=0.2, color="black")
        axes.plot(self.ysum, lw=0.2, color="red")
        axes.plot(range(xlo, xhi+1), self.ysum[xlo:xhi+1], lw=0.2, color="blue")
        print(f"writing {figpath}")
        figure.savefig(figpath)
