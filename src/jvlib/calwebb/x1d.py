from astropy.io.fits import open as fits_open
from numpy import argwhere

from jvlib.util.path import pathlist


class CalwebbX1dMiriMrs(dict):
    '''Manage MIRI MRS 1D spectra extracted by the calwebb pipeline.'''
    def __init__(self, pathspec):
        unsorted = {}
        for path in pathlist(pathspec):
            self._split_x1d_file(unsorted, path)
        for key in sorted(unsorted.keys()):
            self[key] = unsorted[key]

    def _split_x1d_file(self, unsorted, path):
        '''Read MIRI MRS x1d file. Split spectrum into two channels.'''
        with fits_open(path) as hdulist:
            channels = list(hdulist['primary'].header['channel'])
            abc = self._band_to_abc(hdulist['primary'].header['band'])
            dither = hdulist['primary'].header['patt_num']
            dq = hdulist['extract1d'].data['dq']
            middle = len(dq) // 2
            segments = [
                [None, argwhere(dq[:middle] == 0).item(-1) + 1],
                [middle + argwhere(dq[middle:] == 0).item(0), None]]
            for channel, segment in zip(channels, segments):
                key = f'{channel}{abc}.{dither}'
                ib, ie = segment
                wave = hdulist['extract1d'].data['wavelength'][ib:ie]
                flux = hdulist['extract1d'].data['flux'][ib:ie]
                if key in unsorted.keys():
                    raise ValueError(f'Multiple files have key {key}')
                unsorted[key] = {
                    'filename': path.name, 'wave': wave, 'flux':flux}

    def _band_to_abc(self, band):
        return {'SHORT': 'A', 'MEDIUM': 'B', 'LONG': 'C'}[band]
