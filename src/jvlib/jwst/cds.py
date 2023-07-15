from pathlib import Path

from astropy.io.fits import open as fits_open
from matplotlib.animation import FuncAnimation, writers
from matplotlib.figure import Figure
from numpy import (
    concatenate, diff, expand_dims, mean, median, quantile, repeat, reshape,
    sum as np_sum)
from scipy.ndimage import uniform_filter1d

from jvlib.util.path import pathlist


class CdsAssessTso:
    '''Use correlated double samples to assess time series observations.'''
    def __init__(self, paths):
        self.paths = sorted(list(paths))
        self.prefix = self._set_prefix()
        self.cdsint = {}
        self.cdsexp = {}
        self.allpix = 0
        self.trace = {}
        self._process_input_files()
        self._make_cdsexp()
        self._make_all_pixels_light_curve()
        self._trace_spectrum()

    def _make_cdsexp(self):
        '''Calculate mean CDS image for entire exposure.'''
        for det in self.cdsint:
            self.cdsexp[det] = mean(self.cdsint[det], axis=-3)

    def _make_all_pixels_light_curve(self):
        '''Make a light curve by summing all counts on all detectors.'''
        for det in self.cdsint:
            ncds = self.cdsint[det].shape[-3]
            self.allpix += np_sum(self.cdsint[det] * ncds, axis=(-1, -2))

    def _process_input_files(self):
        for path in self.paths:
            print(f'processing {path.name}')
            with fits_open(path) as hdulist:
                self.tgroup = hdulist['primary'].header['tgroup']
                det = hdulist['primary'].header['DETECTOR'].lower()
                cds = diff(hdulist['sci'].data.astype(float), axis=-3)
                cdsint = median(cds, axis=-3)
                try:
                    self.cdsint[det] = concatenate(
                        (self.cdsint[det], cdsint), axis=-3)
                except KeyError:
                    self.cdsint[det] = cdsint

    def _set_prefix(self):
        '''Set the prefix for any output files.'''
        prefixes = [path.name[:25] for path in self.paths]
        assert len(set(prefixes)) == 1
        return prefixes[0]

    def _trace_spectrum(self):
        '''Determine location of spectrum in exposure-level CDS images.'''
        for det in self.cdsexp:
            image = self.cdsexp[det]
            spectrum = np_sum(image, axis=-2)

    def make_figures(self):
        '''Make all figures. Save to current working directory.'''
        self.make_figure_cdsexp()
        self.make_figure_allpix()

    def make_figure_cdsexp(self):
        '''Make figure showing exposure-level CDS image for each detector.'''
        nax = len(self.cdsexp)
        figsize = (14, min(10, 3 * nax + 1))
        figure = Figure(figsize=figsize)
        axlist = figure.subplots(nax, sharex=True)
        for det, ax in zip(self.cdsexp, axlist):
            image = self.cdsexp[det] / self.tgroup
            vmin, vmax = quantile(image, (0.01, 0.995))
            axim = ax.imshow(
                image, vmin=vmin, vmax=vmax,
                interpolation='nearest', origin='lower', aspect='auto')
            ax.text(0.03, 0.85, det, transform=ax.transAxes, color='white')
            figure.colorbar(axim, pad=0.02, fraction=0.06, location='right')
        filename = f'{self.prefix}_cdsexp.pdf'
        print(f'writing {filename}')
        figure.savefig(filename)

    def make_figure_allpix(self):
        '''Make figure showing light curve for sum of all pixels.'''
        figure = Figure(figsize=(10,6))
        axes = figure.subplots()
        axes.plot(self.allpix)
        axes.set_xlabel('Integration Number')
        axes.set_ylabel('Sum over all pixels [ADU]')
        filename = f'{self.prefix}_allpix.pdf'
        print(f'writing {filename}')
        figure.savefig(filename)

class CdsExposureUncal:
    '''Read uncalibrated JWST data for one exposure and detector.'''
    def __init__(self, pathspec):
        self.pathlist = pathlist(pathspec)
        self._check_file_consistency()
        self.data = self._concatenate_segment_files('sci')

    def _check_file_consistency(self):
        first_prefix = None
        for path in self.pathlist:
            prefix, suffix = path.name.rsplit('_', 1)
            if suffix != 'uncal.fits':
                raise ValueError(f'Not an uncal file: {path.name}')
            if not first_prefix:
                first_prefix = prefix
            if prefix != first_prefix:
                raise ValueError('Multiple exposures specified')

    def _process_input_files(self):
        cds = None
        for path in self.pathlist:
            with fits_open(path) as hdulist:
                segment = diff(hdulist['sci'].data.astype(float), axis=-3)
                if cds:
                    cds = concatenate(cds, segment), axis=-3)
                else:
                    cds = segment

class CdsMiriRefout:
    '''Compute and fit CDS differences of REFOUT from a JWST/MIRI uncal file.

    CDS is the difference between consecutive groups in each integration.'''
    def __init__(self, path):
        self.path = Path(path).expanduser()
        self.cds = self.read_uncal_file(self.path)
        self.fit = self.fit_cds()

    def read_uncal_file(self, path):
        '''Read REFOUT data from MIRI uncal file. Compute and return CDS.

        Fix sizes of fast and slow readout axes, if wrong due to bug.'''
        with fits_open(path) as hdulist: 
            cds = diff(hdulist['refout'].data.astype(float), axis=-3)
            nint, ncds, nslow, nfast = cds.shape
            # fix bug: NAXIS1 and NAXIS2 wrong in REFOUT extension
            if nfast == hdulist['sci'].shape[-1]:
                nslow *= 4
                nfast //= 4
                cds = reshape(cds, (nint, ncds, nslow, nfast))
            return reshape(repeat(cds, 4), (nint, ncds, nslow, 4 * nfast))

    def fit_cds(self):
        '''Fit CDS images with a smooth model.'''
        shape = self.cds.shape
        nfast = shape[-1]
        self.smfast = reshape(repeat(mean(self.cds, axis=-1), nfast), shape)
        self.smslow = uniform_filter1d(self.smfast, 12, axis=-2, mode='nearest')
        return self.smfast - self.smslow


class CdsMiriRefoutMovie:
    '''Create movie that steps through data in CdsMiriRefout object.'''
    def __init__(self, data):
        for name in ['cds', 'fit', 'smfast', 'smslow']:
            setattr(self, name, getattr(data, name))
        self.vlim = quantile(self.cds, [0.02, 0.98])
        self.init_figure()
        self.fps = 30
        nint, ncds = self.cds.shape[:2]
        self.movie = FuncAnimation(
            self.fig, self.update_figure, frames=nint*ncds,
            interval=1000/self.fps)

    def get_images(self, iint, icds):
        '''Return images to show for the specified integration and CDS.'''
        return [
            self.cds[iint, icds, :, :],
            self.cds[iint, icds, :, :] - self.smfast[iint, icds, :, :],
            self.smfast[iint, icds, :, :],
            self.smslow[iint, icds, :, :], 
            self.smfast[iint, icds, :, :] - self.smslow[iint, icds, :, :]]

    def init_figure(self):
        '''Initialize figure and axes that will be used for each frame.'''
        images = self.get_images(0, 0)
        nimage = len(images)
        self.fig = Figure(figsize=(14, 10), dpi=150)
        self.axes = self.fig.subplots(1, nimage, sharey=True)
        self.axim = [None] * nimage
        for i in range(nimage):
            self.axim[i] = self.axes[i].imshow(
                images[i], vmin=self.vlim[0], vmax=self.vlim[1],
                interpolation='nearest', origin='lower', aspect='auto')
            self.fig.colorbar(
                self.axim[i], pad=0.02, fraction=0.06, location='top')

    def update_figure(self, frame_index):
        '''Change data in figure to specifed plane in cube.'''
        ncds = self.cds.shape[1]
        iint = frame_index // ncds
        icds = frame_index % ncds
        images = self.get_images(iint, icds)
        for axim, image in zip(self.axim, images):
            axim.set_data(image)

    def save_mp4(self, path):
        '''Write movie to disk file.'''
        writer = writers["ffmpeg"](fps=self.fps)
        self.movie.save(path, writer, dpi=150)


class CdsUncal:
    '''Use correlated double samples to process a JWST uncal file.'''
    def __init__(self, path):
        self.path = Path(path)
        with fits_open(path) as hdulist:
            self.meta = _set_meta(hdulist)
            self.scihead = hdulist['sci'].header
            self.sci = diff(hdulist['sci'].data.astype(float), axis=-3)

    def _set_meta(self, hdulist):
        '''Populate metadata dictionary with info from uncal headers.'''
        prihead = hdulist['primary'].heaser
        meta = dict(
            inst=prihead['INSTRUME'],
            det=prihead['DETECTOR'])
        return meta
