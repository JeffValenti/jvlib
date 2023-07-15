from astropy.stats import SigmaClip
import numpy as np

from jvlib.reduce.figure import FigureImshow, FigurePlot
from jvlib.reduce.jwst import JwstUncalExposure
from jvlib.util.debug import MonitorTimeMemory


class NrstsCdsPipeline:
    '''Process NIRSpec time series data, using differences up the ramp.

    Notes
    -----
    CDS refers to correlated double sample, which in this case means we
    analyze the difference between consecutive groups up the rame, rather
    than the measured groups up the ramp. This removes some systematic noise.
    '''

    def __init__(self, path, root=''):
        monitor = MonitorTimeMemory(autoprint=True)
        self.uncal = JwstUncalExposure(path)
        monitor('after reading int16 uncal data')
        self.cds_cube = self.uncal.get_cds_cube()
        monitor('after getting real32 cds_cube')
        sigmaclip = SigmaClip(cenfunc='median', stdfunc='mad_std')
        cds_image = np.nanmean(sigmaclip(
            self.cds_cube, axis=(0, 1), masked=False, copy=True), axis=(0, 1))
        monitor('after making cds_image')
        np.savez_compressed(f'{root}_cds_image.npz', cds_image=cds_image)
        monitor('after writing cds_image')
        FigureImshow(cds_image, path=f'{root}_cds_image.pdf')
