from pathlib import Path

from astropy.io.fits import open as fits_open
import numpy as np


INSTRUME = {
    'FGS': 'fgs',
    'MIRI': 'mir',
    'NIRCAM': 'nrc',
    'NIRISS': 'nis',
    'NIRSPEC': 'nrs'}

TEMPLATE = {
    'NIRSpec Bright Object Time Series': 'nrsbots',
    }

class JwstUncalExposure:
    '''Handle JWST uncalibrated exposure data, which may be segmented.'''

    def __init__(self, path):
        self._nseg, self._pathlist = self._check_for_segments(path)
        self.prihead, self.scihead = self._read_header()
        self.scidata = self._read_scidata()

    def _check_for_segments(self, path):
        '''Return number of segment files and list of paths to files.

        Parameters
        ----------
        path : str or Path object
           Location of _uncal.fits file, may be a segmented file.

        Returns
        -------
        nseg : int
            Number of exposure segments, 0 for an unsegmented exposure.
        pathlist : List of Path objects
            Resolved path(s) of exposure file(s).
        '''
        resolved_path = Path(path).expanduser().resolve()
        with fits_open(resolved_path) as hdulist:
            prihead = hdulist['PRIMARY'].header
        if 'EXSEGNUM' in prihead:
            nseg = prihead['EXSEGNUM']
            parent = resolved_path.parent
            pre, post = resolved_path.name.split('-seg')
            pathlist = [
                parent / f'{pre}-seg{i+1:03}{post[3:]}' for i in range(nseg)]
        else:
            nseg = 0
            pathlist = [resolved_path]
        return nseg, pathlist

    def _read_header(self):
        '''Return primary header and header for SCI extension.

        Returns
        -------
        prihead : astropy.io.fits.header.Header
            Primary header from first file in pathlist.
        scihead : astropy.io.fits.header.Header
            Header for SCI extension from first file in pathlist.
        '''
        path = self.pathlist[0]
        with fits_open(path) as hdulist:
            prihead = hdulist['PRIMARY'].header
            scihead = hdulist['SCI'].header
        return prihead, scihead

    def _read_scidata(self):
        '''Return concatenated data from SCI extension in all files.

        Returns
        -------
        scidata : numpy.ndarray
            Concatenated data from SCI extension of all files in pathlist.

        Notes
        -----
        To reduce persistent memory, we keep dtype=np.uint16, as in uncal file.
        To reduce peak memory, we preallocate scidata and insert segment data.
        '''
        # scidata = None
        if self.nseg <= 1:
            path = self.pathlist[0]
            with fits_open(path) as hdulist:
                scidata = hdulist['SCI'].data
        else:
            scidata = np.empty(self.expdim, dtype=np.uint16)
            for path in self.pathlist:
                with fits_open(path) as hdulist:
                    ibeg = hdulist['PRIMARY'].header['INTSTART'] - 1
                    iend = hdulist['PRIMARY'].header['INTEND']
                    scidata[ibeg:iend,:,:,:] = hdulist['SCI'].data
        return scidata

    @property
    def expdim(self):
        return (
            self.prihead['NINTS'],
            self.prihead['NGROUPS'],
            self.prihead['SUBSIZE2'],
            self.prihead['SUBSIZE1'])

    @property
    def exptype(self):
        return self.prihead['EXP_TYPE']

    @property
    def fast(self):
        return self.prihead['FASTAXIS'] - 1

    @property
    def inst(self):
        return INSTRUME[self.prihead['INSTRUME']]

    @property
    def nseg(self):
        return self._nseg

    @property
    def pathlist(self):
        return self._pathlist

    @property
    def template(self):
        return TEMPLATE[self.prihead['TEMPLATE']]

    @property
    def visit(self):
        return self.prihead['VISIT_ID']

    def get_cds_cube(self, dtype=np.single):
        '''Return difference between consecutive groups in each integration.

        Parameters
        ----------
        dtype : type
            Data type for elements in cds_cube (default: np.single)

        Returns
        -------
        cds_cube : numpy.ndarray
            Difference between consecutive groups in each integration


        Notes
        -----
        To reduce downstream memory, default is to return dtype=np.single.
        '''
        cds_cube = np.diff(self.scidata, axis=-3)
        return cds_cube.astype(dtype)
