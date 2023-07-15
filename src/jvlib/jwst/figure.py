from matplotlib.colors import TABLEAU_COLORS
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter


class FigureMrsSpectrum:
    '''Create figures showing an MRS spectrum.

    Parameters:
        spectrum - dict of dict - wave and flux for each MRS channel
    '''
    def __init__(self, spectrum):
        self.spectrum = spectrum
        self.color = [f'tab:'{c} for c in [
            'red', 'orange', 'brown', 'green', 'blue', 'purple']

    def make_overview(self, figsize=(14, 8)):
        self.overview_figure = Figure(figsize=figsize)
        self.overview_axes = self.overview_figure.subplots()
        for i, channel in enumerate(self.spec):
            wave = self.spectrum[channel]['wave']
            flux = self.spectrum[channel]['flux']
            color = self.color[i // len(self.color)]
            self.overview.axes.plot(wave, flux, color=color)
