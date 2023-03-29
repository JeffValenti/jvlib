#!/usr/bin/env python

from math import ceil, sqrt
from pathlib import Path

from astropy.io.fits import open as fits_open
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from numpy import (
    argwhere, diff as np_diff, flip, median as np_median, sum as np_sum, swapaxes)
from scipy.ndimage import median_filter

from jvlib.util.obj import use_or_set_default


class UncalData:
    def __init__(self, path):
        self.path = Path(path)
        self.hdulist = fits_open(path)
        self.phead = self.hdulist["primary"].header
        self.xhead = self.hdulist["sci"].header
        self.set_metadata()
        self.maxpanel = 6
        self.margins = dict(
            left=0.03, right=0.98, bottom=0.04, top=0.96, hspace=0.06)

    def set_metadata(self):
        """Read expoure metadata from FITS primary header."""
        pkeys = [
            "detector", "filter", "grating", "fxd_slit", "patt_num",
            "nints", "ngroups", "subarray"]
        for key in pkeys:
            try:
                self.__dict__[key] = self.phead[key]
            except KeyError:
                self.__dict__[key] = None
        self.ndim = self.xhead["naxis"]
        self.config = f"{self.detector}_{self.grating}_{self.filter}" \
            f"_{self.fxd_slit}_DP{self.patt_num}"

    def load_integ_data(self, integ):
        """Load science data for specified integration from FITS file."""
        if self.ndim == 4:
             data = self.hdulist["sci"].data[integ, :, :, :].astype(float)
        else:
             assert integ == 0
             data = self.hdulist["sci"].data.astype(float)
        if self.subarray == "SLITLESSPRISM":
            return flip(swapaxes(data, 1, 2), 2)
        else:
            return data

    def calc_group_diff(self, integ, rebase=True):
        """Calculate difference between consecutive groups in integration."""
        integ_data = self.load_integ_data(integ)
        group_diff = np_diff(integ_data, axis=0)
        if rebase:
            for igroup in range(self.ngroups - 1):
                image = group_diff[igroup, :, :]
                for i in range(image.shape[0]):
                     group_diff[igroup, :, :] = image - np_median(image[i, :])
        return group_diff

    def calc_median_group_diff(self, integ, rebase=True):
        """Calculate median of all group difference images in integration."""
        group_diff = self.calc_group_diff(integ, rebase=rebase)
        return np_median(group_diff, axis=0)

    def close_file(self):
        """Close the FITS file, once access is no longer needed."""
        self.hdulist.close()
        return

    def init_figure(self, npanel):
        fig = Figure(figsize=(14, 8))
        fig.suptitle(f"{self.config},  {self.path.name}")
        fig.subplots_adjust(**self.margins)
        axes = fig.subplots(npanel, sharex=True)
        return fig, axes

    def plot_groups(self, integ, vlim=None, figpath=None):
        integ_data = self.load_integ_data(integ)
        npanel = min(self.ngroups, self.maxpanel)
        npage = ceil(self.ngroups / npanel)
        if figpath is None:
            figpath = f"{self.path.stem}_groups_i{integ}.pdf"
        print(f"writing {figpath}")
        with PdfPages(figpath) as pdf:
            for group in range(self.ngroups):
                image = integ_data[group, :, :]
                if vlim is None:
                    medim = np_median(image)
                    vhw = 5 * np_median(abs(image - medim))
                    vlim = [medim - vhw, medim + vhw]
                panel = group % npanel
                if panel == 0:
                    fig, axes = self.init_figure(npanel)
                ax = axes[panel]
                ax.imshow(
                    image, origin="lower", aspect="auto", cmap="gray",
                    vmin=vlim[0], vmax=vlim[1], interpolation="nearest")
                ax.text(
                    1.005, 0.5, f"G{group}", va="center",
                    rotation="vertical", transform=ax.transAxes)
                if panel == npanel - 1:
                    pdf.savefig(fig)
            if panel < npanel - 1:
                for p in range(panel, npanel):
                    axes[p].axis("off")

    def plot_group_diffs(self, integ, rebase=True, vlim=None, figpath=None):
        group_diff = self.calc_group_diff(integ, rebase=rebase)
        npanel = min(self.ngroups, self.maxpanel)
        npage = ceil(self.ngroups / npanel)
        if figpath is None:
            figpath = f"{self.path.stem}_gdiffs_i{integ}.pdf"
        print(f"writing {figpath}")
        with PdfPages(figpath) as pdf:
            for group in range(self.ngroups - 1):
                image = group_diff[group, :, :]
                if vlim is None:
                    medim = np_median(image)
                    vhw = 5 * np_median(abs(image - medim))
                    vlim = [medim - vhw, medim + vhw]
                panel = group % npanel
                if panel == 0:
                    fig, axes = self.init_figure(npanel)
                ax = axes[panel]
                ax.imshow(
                    image, origin="lower", aspect="auto", cmap="gray",
                    vmin=vlim[0], vmax=vlim[1], interpolation="nearest")
                ax.text(
                    1.005, 0.5, f"G{group + 1}-G{group}", va="center",
                    rotation="vertical", transform=ax.transAxes)
                if panel == npanel - 1:
                    pdf.savefig(fig)
            if panel < npanel - 1:
                for p in range(panel, npanel):
                    axes[p].axis("off")

class UncalDataList(list):
    def __init__(self):
        pass

    @property
    def configs(self):
        return sorted(list(set([uncal.config for uncal in self])))

    def get(self, config):
        for uncal in self:
            if uncal.config == config:
                return uncal
        raise ValueError("No image for config={config}")
