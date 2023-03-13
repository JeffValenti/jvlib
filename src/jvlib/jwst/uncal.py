#!/usr/bin/env python

from math import ceil, sqrt
from pathlib import Path

from astropy.io.fits import open as fits_open
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from numpy import argwhere, diff as np_diff, median, sum as np_sum
from scipy.ndimage import median_filter

from jvlib.util.obj import use_or_set_default


class UncalData:
    def __init__(self, path):
        self.path = path
        self.name = self.path.name
        self.hdulist = fits_open(path)
        self.phead = self.hdulist["primary"].header
        self.xhead = self.hdulist["sci"].header
        self.set_metadata()

    def set_metadata(self):
        """Read expoure metadata from FITS primary header."""
        pkeys = [
            "detector", "filter", "grating", "fxd_slit", "patt_num",
            "nints", "ngroups"]
        for key in pkeys:
            self.__dict__[key] = self.phead[key]
        self.config = f"{self.detector}_{self.grating}_{self.filter}" \
            f"_{self.fxd_slit}_DP{self.patt_num}"
        self.ndim = self.xhead["naxis"]

    def load_integ_data(self, integ):
        """Load science data for specified integration from FITS file."""
        if self.ndim == 4:
             return self.hdulist["sci"].data[integ, :, :, :].astype(float)
        else:
             assert integ == 0
             return self.hdulist["sci"].data.astype(float)

    def calc_group_diff(self, integ, rebase=True):
        """Calculate difference between consecutive groups in integration."""
        integ_data = self.load_integ_data(integ)
        group_diff = np_diff(integ_data, axis=0)
        if rebase:
            for igroup in range(self.ngroups - 1):
                image = group_diff[igroup, :, :]
                group_diff[igroup, :, :] = image - median(image, axis=0)
        return group_diff

    def calc_median_group_diff(self, integ, rebase=True):
        """Calculate median of all group difference images in integration."""
        group_diff = self.calc_group_diff(integ, rebase=rebase)
        return median(group_diff, axis=0)

    def set_median_group_diff(self, rebase=True):
        self.median_group_diff = []
        for integ in range(self.nints):
            self.median_group_diff.append(
                self.calc_median_group_diff(integ, rebase=rebase))

    def close_file(self):
        """Close the FITS file, once access is no longer needed."""
        self.hdulist.close()
        return


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
