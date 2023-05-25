from math import exp, log
from pathlib import Path
from webbrowser import open as webbrowser_open

from astropy.table import Column, Table
from matplotlib.axes import Axes
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from numpy import (
    ceil, diff, full, isfinite, isnan, mean, median,
    nan, nanmax, nanmin, searchsorted)
from scipy.interpolate import splantider, splev, splrep

from jvlib.spec.wave import make_geomwave


class BaseSpectrum:
    '''Manage data for a spectrum.

    Examples:
        from jvlib.spec.base import BaseSpectrum
        spec = BaseSpectrum(wave, flux, fsig, ok)
        spec = Basespectrum(wave=wave, flux=flux, fsig=fsig, ok=ok)
        spec = Basespectrum(dict(wave=wave, flux=flux, fsig=fsig, ok=ok))
        spec = Basespectrum(BaseSpectrum(wave, flux, fsig, ok))
    '''
    def __init__(self, *args, **kwargs):
        self.attr_required = ['wave', 'flux']
        self.attr_defaults = dict(fsig=None, ok=None, label=None)
        narg = len(args)
        if narg >= 2:
            self._set_attributes_from_args(args)
        elif narg == 1:
            if isinstance(args[0], BaseSpectrum):
                self._set_attributes_from_attr(args[0])
            elif narg == 1 and isinstance(args[0], dict):
                self._set_attributes_from_dict(args[0])
            else:
                raise ValueError(
                    'BaseSpectrum got unexpected argument type')
        elif narg == 0:
            self._set_attributes_from_dict(kwargs)
        if self.ok is None:
            self.ok = isfinite(self.flux)
        self.wmin = nanmin(self.wave)
        self.wmax = nanmax(self.wave)

    def _set_attributes_from_args(self, args):
        '''Set instance attributes based on positional arguments.'''
        for iarg, key in enumerate(self.attr_required):
            setattr(self, key, args[iarg])
        nreq = len(self.attr_required)
        narg = len(args)
        for i, key in enumerate(self.attr_defaults):
            iarg = nreq + i
            if iarg < narg:
                setattr(self, key, args[iarg])
            else:
                setattr(self, key, self.attr_defaults[key])

    def _set_attributes_from_dict(self, attr_dict):
        '''Set instance attributes based on input dictionary.'''
        for key in self.attr_required:
            setattr(self, key, attr_dict[key])
        for key, default in self.attr_defaults.items():
            try:
                setattr(self, key, attr_dict[key])
            except KeyError:
                setattr(self, key, default)

    def _set_attributes_from_attr(self, attr_object):
        '''Set instance attributes based on input object with attributes.'''
        for key in self.attr_required:
            setattr(self, key, getattr(attr_object, key))
        for key, default in self.attr_defaults.items():
            try:
                setattr(self, key, getattr(attr_object, key))
            except AttributeError:
                setattr(self, key, default)

    def interpolate(self, wave_new):
        '''Return spectrum interpolated onto new wavelength scale.'''
        wave_ok = self.wave[self.ok]
        flux_ok = self.flux[self.ok]
        fsig_ok = self.fsig[self.ok]
        spline_param = splrep(wave_ok, flux_ok)
        flux_new = splev(wave_new, spline_param)
        spline_param = splrep(wave_ok, fsig_ok)
        fsig_new = splev(wave_new, spline_param)
        lo = searchsorted(wave_new, wave_ok[0], 'left')
        hi = searchsorted(wave_new, wave_ok[-1], 'right')
        return BaseSpectrum(wave_new[lo:hi], flux_new[lo:hi], fsig_new[lo:hi])

    def bin(self, wave_new, edges_new):
        '''Return spectrum interpolated onto new wavelength scale.'''
        wave_ok = self.wave[self.ok]
        flux_ok = self.flux[self.ok]
        # fsig_ok = self.fsig[self.ok]
        spline_param = splrep(wave_ok, flux_ok)
        integral_param = splantider(spline_param)
        wave_left = edges_new[:-1]
        wave_right = edges_new[1:]
        integral_left = splev(wave_left, integral_param)
        integral_right = splev(wave_right, integral_param)
        flux_new = (integral_right - integral_left) / (wave_right - wave_left)
        lo = searchsorted(wave_new, wave_ok[0], 'left')
        hi = searchsorted(wave_new, wave_ok[-1], 'right')
        # calculate fsig_new and pass fsig_new as third argument in line below
        return BaseSpectrum(wave_new[lo:hi], flux_new[lo:hi], flux_new[lo:hi])

    def plot(self, path=None, browse=False):
        '''Make simple plot of spectrum.'''
        figure = Figure(figsize=(12, 6))
        axes = figure.subplots()
        axes.set_xlabel('Wavelength')
        axes.set_ylabel('Flux')
        axes.plot(self.wave[self.ok], self.flux[self.ok], lw=0.1)
        if path is None:
            return figure, axes
        figure.savefig(path)
        print(f'wrote {path}')
        if browse:
            webbrowser_open(Path(path).absolute().as_uri())
            input('press enter to continue')


class SpectrumList(list):
    '''Manage a list of spectrum objects.'''
    def __init__(self, *args):
        list.__init__(self, *args)

    def _calc_figure_xlims(self, margin=0.01, density=1e30):
        '''Return xaxis limits for one or more figures.'''
        wmin = self.wmin
        wmax = self.wmax
        med_wratio = self.median_wratio
        wgeom, wedge = make_geomwave(wmin, wmax, med_wratio)
        nfig = int(ceil(len(wgeom) / density))
        fig_wratio = exp(log(wmax / wmin) / nfig)
        _, figedge = make_geomwave(wmin, wmax, fig_wratio)
        return [
            [wlo / (1 + margin), whi * (1 + margin)]
            for wlo, whi in zip(figedge[:-1], figedge[1:])]

    @property
    def info(self):
        '''Return table of information about consitutent spectra.'''
        table = Table()
        table['label'] = [s.label for s in self]
        table['wmin'] = Column([s.wmin for s in self], format='.4f')
        table['wmax'] = Column([s.wmax for s in self], format='.4f')
        table['name'] = [s.path.name for s in self]
        return table

    @property
    def wmin(self):
        '''Return minimum wavelength with finite flux for all spectra.'''
        return min([min(spec.wave[spec.ok]) for spec in self])

    @property
    def wmax(self):
        '''Return maximum wavelength with finite flux for all spectra.'''
        return max([max(spec.wave[spec.ok]) for spec in self])

    @property
    def median_wratio(self):
        '''Return median ratio of consecutive wavelengths in spectra.'''
        wratio = []
        for spectrum in self:
            wratio.extend(spectrum.wave[1:] / spectrum.wave[:-1])
        return median(wratio)

    def make_figure(
            self, path, ytype='flux', margin=0.01, xlim=None, browse=False):
        '''Plot overview of flux or dispersion for spectra in list.'''
        labels = self.info['label']
        if xlim is None:
            xlim = self._calc_figure_xlims(margin=margin)[0]
        figure = Figure(figsize=(12, 6))
        axes = figure.subplots()
        axes.set_xlim(*xlim)
        if xlim[1] / xlim[0] >= 2:
            axes.set_xscale('log')
            xformatter = FuncFormatter(lambda x, _: '{:.16g}'.format(x))
            axes.xaxis.set_major_formatter(xformatter)
            axes.xaxis.set_minor_formatter(xformatter)
        ylims = []
        for i in range(len(self)):
            spec = self[i]
            if ytype == 'flux':
                x = spec.wave
                y = spec.flux.copy()
                y[spec.ok == False] = nan
                u = spec.fsig.copy()
                ylabel = f'Flux  [{spec.fluxunit}]'
                lw = 0.2
            elif ytype == 'disp':
                x = (spec.wave[:-1] + spec.wave[1:]) / 2
                y = diff(spec.wave)
                y[y > 10 * sum(y) / len(y)] = nan
                ylabel = f'Dispersion  [{spec.waveunit}]'
                lw = 0.5
            elif ytype == 'wrat':
                x = (spec.wave[:-1] + spec.wave[1:]) / 2
                y = spec.wave[1:] / spec.wave[:-1] - 1
                y[y > 10 * sum(y) / len(y)] = nan
                ylabel = f'Wave[i+1] / Wave[i] - 1'
                lw = 0.5
            else:
                raise ValueError(f'unknown ytype: {ytype}')
            yvisible = y[(x >= xlim[0]) & (x <= xlim[1])]
            if (len(yvisible) == 0) or isnan(yvisible).all():
                continue
            ylo = nanmin(yvisible)
            yhi = nanmax(yvisible)
            ylims.append(
                [ylo - margin * (yhi - ylo), yhi + margin * (yhi - ylo)])
            axes.plot(x, y, lw=lw, label=labels[i])
        ylo = min([y[0] for y in ylims])
        yhi = max([y[1] for y in ylims])
        ylim = [ylo - margin * (yhi - ylo), yhi + margin * (yhi - ylo)]
        axes.set_ylim(*ylim)
        if ytype == 'wrat':
            medrat = self.median_wratio
            x = [xlim[0] * (1 + margin), xlim[1] / (1 + margin)]
            y = [medrat - 1, medrat - 1]
            axes.plot(x, y, '--', color='lightgray')
        axes.set_xlabel(f'Wavelength  [{spec.waveunit}]')
        axes.set_ylabel(ylabel)
        legend = axes.legend()
        for legobj in legend.legendHandles:
            legobj.set_linewidth(2)
        if path:
            figure.savefig(path, bbox_inches='tight', pad_inches = 0.1)
            print(f'wrote {path}')
        else:
            return figure
        if browse:
            webbrowser_open(Path(path).absolute().as_uri())

    def save_pdf(
            self, path, ytype='flux', margin=0.01,
            density=300, browse=False):
        '''Plot details of flux or dispersion for spectra in list.'''
        label = self.info['label']
        xlims = self._calc_figure_xlims(margin=margin, density=density)
        with PdfPages(path) as pdf:
            for xlim in xlims:
                figure = self.make_figure(
                    path=None, margin=margin, xlim=xlim, browse=browse)
                pdf.savefig(figure)
        print(f'wrote {path}')
        if browse:
            webbrowser_open(Path(path).absolute().as_uri())


class SpectrumAxes:
    '''Plot BaseSpectrum data in matplotlib.axes.Axes object.'''

    def __init__(
            self, spec, axes, plottype='flux', errorbar=False,
            xlim=None, xmargin=0.01, ylim=None, ymargin=0.01,
            legend=True):
        self._speclist = speclist(spec)
        self.axes = axes
        self._plottype = plottype
        self._errorbar = errorbar
        self._xlim = xlim
        self._xmargin = xmargin
        self._ylim = ylim
        self._ymargin = ymargin
        self._legend = legend
        self.segments = []
        self._plot()
        self._update_axes_limits()

    def _calc_axis_limits(self, data, margin):
        '''Calculate default axis limits, given data and margin.'''
        minval = min(data)
        maxval = max(data)
        span = maxval - minval
        return [minval - margin * span, maxval + margin * span]

    def _get_plot_data(self, spec):
        '''Get data from current spectrum for plottype.'''
        if self._plottype == 'flux':
            x = spec.wave
            y = spec.flux.copy()
            u = spec.fsig
            ok = spec.ok
            y[ok == False] = nan
            ylabel = f'Flux ({spec.fluxunit})'
        elif self._plottype in ['disp', 'frac']:
            x = (spec.wave[:-1] + spec.wave[1:]) / 2
            if self._plottype == 'disp':
                y = diff(spec.wave)
                ylabel = f'Dispersion, $\Delta\lambda$ ({spec.waveunit})'
            elif self._plottype == 'frac':
                y = spec.wave[1:] / spec.wave[:-1] - 1
                ylabel = f'$\Delta\lambda / \lambda$'
            else:
                raise ValueError(f'unknown plottype: {plottype}')
            y[y > 10 * mean(y)] = nan
            ok = full(len(x), True)
            u = None
        else:
            raise ValueError(f'unknown plottype: {plottype}')
        xlabel = f'Wavelength ({spec.waveunit})'
        return x, y, u, ok, xlabel, ylabel

    def _plot(self):
        '''Plot each spectrum in the axes. Save min and max values.'''
        bounds = []
        for spec in self._speclist:
            x, y, u, ok, xlabel, ylabel = self._get_plot_data(spec)
            if self._errorbar and u is not None:
                segment = self.axes.errorbar(x, y, u, label=spec.label)
            else:
                segment = self.axes.plot(x, y, label=spec.label)
            self.segments.extend(segment)
            bounds.append([nanmin(x), nanmax(x), nanmin(y), nanmax(y)])
        bounds = list(zip(*bounds))
        self._xminmax = [nanmin(bounds[0]), nanmax(bounds[1])]
        self._yminmax = [nanmin(bounds[2]), nanmax(bounds[3])]
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        if self._legend is True:
            if any([spec.label for spec in self._speclist]):
                self.axes.legend(fontsize='small')

    def _update_axes_limits(self):
        '''Update axes limits, if not already specified.'''
        if self._xlim is None:
            self._xlim = self._calc_axis_limits(self._xminmax, self._xmargin)
        self.axes.set_xlim(self._xlim)
        if self._xlim[1] / self._xlim[0] >= 2:
            self.axes.set_xscale('log')
            xformatter = FuncFormatter(lambda x, _: '{:.16g}'.format(x))
            self.axes.xaxis.set_major_formatter(xformatter)
            self.axes.xaxis.set_minor_formatter(xformatter)
        if self._ylim is None:
            self._ylim = self._calc_axis_limits(self._yminmax, self._ymargin)


class SpectrumMultiPagePdf:
    '''Make multi-page PDF plot of data in SpectrumList object.'''

    def __init__(
            self, spec, pdfpath,
            xmargin=0.01, ymargin=0.01, density=1000,
            errorbar=True, legend=True, auto=True):
        self._speclist = speclist(spec)
        self._pdfpath = pdfpath
        self._xmargin = xmargin
        self._ymargin = ymargin
        self._density = density
        self._errorbar = errorbar
        self._legend = legend
        self.xlims = self._calc_xlims()
        if auto:
            self.auto()
        else:
            self.pdf = PdfPages(self._pdfpath)

    def _calc_xlims(self):
        '''Return xaxis limits for one or more figures.'''
        wmin = self._speclist.wmin
        wmax = self._speclist.wmax
        med_wratio = self._speclist.median_wratio
        wgeom, wedge = make_geomwave(wmin, wmax, med_wratio)
        nfig = int(ceil(len(wgeom) / self._density))
        fig_wratio = exp(log(wmax / wmin) / nfig)
        _, figedge = make_geomwave(wmin, wmax, fig_wratio)
        return [
            [wlo / (1 + self._xmargin), whi * (1 + self._xmargin)]
            for wlo, whi in zip(figedge[:-1], figedge[1:])]

    def auto(self):
        with PdfPages(self._pdfpath) as pdf:
            for xlim in self.xlims:
                figure, axes, specaxes = self.makefig(xlim)
                figure.tight_layout()
                pdf.savefig(figure)

    def close(self):
        '''Write current axes to PDF file.'''
        self.pdf.close()

    def savefig(self):
        '''Convenince function equivalent ot self.pdf.savefig().'''
        self.pdf.savefig()

    def makefig(self, xlim):
        '''Return SpectrumAxes object for specified xaxis plot limits.'''
        figure = Figure()
        axes = figure.subplots()
        specaxes = SpectrumAxes(
            self._speclist, axes, xlim=xlim, xmargin=0,
            errorbar=self._errorbar, legend=self._legend)
        return figure, axes, specaxes


def speclist(spec):
    '''Return a SpectrumList object for one or more input spectra.'''
    if isinstance(spec, SpectrumList):
        return spec
    elif isinstance(spec, BaseSpectrum):
        speclist = SpectrumList()
        speclist.append(spec)
        return speclist
    else:
        raise ValueError('spec must be SpectrumList or BaseSpectrum')
