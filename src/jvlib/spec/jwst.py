from pathlib import Path

from astropy.io.fits import open as fits_open
from astropy.units import micron, mJy
from numpy import isfinite, squeeze

from jvlib.spec.base import BaseSpectrum
from jvlib.util.numpy import print_all


class NirspecFixedSlitSpectrum(BaseSpectrum):
    '''Manage a NIRSpec fixed slit spectrum from an _x1d.fits file.'''

    def __init__(self, path):
        self.path = Path(path).expanduser().absolute().resolve()
        with fits_open(self.path) as hdulist:
            self.prihead = hdulist['primary'].header.copy()
            self.fxd_slit = self.prihead['fxd_slit']
            extension = self._get_extension_for_slit(hdulist, self.fxd_slit)
            self.exthead = extension.header.copy()
            self.waveunit = extension.columns['wavelength'].unit
            if self.waveunit == 'um':
                self.waveunit = 'µm'
            fluxscale = 1
            self.fluxunit = extension.columns['flux'].unit
            if extension.columns['flux'].unit == 'Jy':
                fluxscale = 1000
                self.fluxunit = 'mJy'
            wave = extension.data['wavelength']
            flux = extension.data['flux'] * fluxscale
            fsig = extension.data['flux_error'] * fluxscale
            print_all(fsig)
            exit()
            fok = isfinite(flux) & (flux != 0) & (extension.data['dq'] == 0)
            super().__init__(wave, flux, fsig, fok)
            self.label = self._get_label()

    def _get_extension_for_slit(self, hdulist, fxd_slit):
        '''Find FITS extension with extracted spectrum for specified slit.'''
        for extver in range(1, 6):
            extension = hdulist[('extract1d', extver)]
            if extension.header['sltname'] == fxd_slit:
                return extension
        raise ValueError(f'no extension for fxd_slit={fxd_slit}')

    def _get_label(self):
        '''Return label that identifies this spectrum.'''
        label = f"{self.prihead['grating']} " \
             f"{self.prihead['filter']} " \
             f"{self.prihead['fxd_slit']}"
        return label
