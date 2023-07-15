from matplotlib.figure import Figure
import numpy as np


class FigureImshow:
    '''Create a figure that shows in image.'''

    def __init__(
            self, image,
            vquantile=(0.16, 0.84), dpi=1024, path=None):
        vmin, vmax = np.quantile(image, vquantile)
        self.fig = Figure(dpi=dpi)
        self.axes = self.fig.subplots()
        self.axesimage = self.axes.imshow(
            image, origin='lower', aspect='auto',
            interpolation='nearest', vmin=vmin, vmax=vmax)
        self.fig.colorbar(self.axesimage, pad=0.02, fraction=0.06)
        if path:
            self.savefig(path)

    def savefig(self, path):
        '''Save figure and print notification'''
        self.fig.tight_layout()
        self.fig.savefig(path)
        print(f'wrote {path}')


class FigurePlot:
    '''Create a figure that plots a curve.'''

    def __init__(
            self, x, y,
            lw=1, path=None):
        self.fig = Figure()
        self.axes = self.fig.subplots()
        self.axes.plot(x, y, lw=lw)
        if path:
            self.savefig(path)

    def savefig(self, path):
        '''Save figure and print notification'''
        self.fig.tight_layout()
        self.fig.savefig(path)
        print(f'wrote {path}')
