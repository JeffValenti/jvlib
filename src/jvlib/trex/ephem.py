from astropy.time import Time
from numpy import array, sqrt as np_sqrt
from numpy.polynomial.polynomial import Polynomial


class BaseEphemeris:
    """Handle the orbital ephemeris for a transiting exoplanet.

    Cumulative phase is integer orbit number since the reference transit
    plus orbital phase in specified orbit. Negative orbit number indicates
    an orbit that precedes the reference transit.
    
    If an ephemeris has more than two parameters, then generally orbital
    period is a function of time.
    """
    def __init__(self, param, uparam=None, scale='tdb', ref=''):
        self.param = array(param)
        self.uparam = array(uparam) if uparam else None
        self.scale = scale
        self.ref = ref

class PolynomialEphemeris(BaseEphemeris):
    """Handle a polynomial ephemeris for a transiting exoplanet."""

    def predict_time(self, cphase):
        """Use ephemeris to predict time at specified cumulative phases."""
        self.ucphase = None
        self.cphase = array(cphase)
        polynomial = Polynomial(self.param)
        jd = polynomial(self.cphase)
        self.time = Time(jd, format="jd", scale=self.scale)
        if self.uparam is None:
            self.utime = None
        else:
            upolynomial = Polynomial(self.uparam**2)
            self.utime = np_sqrt(upolynomial(self.cphase**2))

    def predict_cphase(self, time):
        """Use ephemeris to predict cumulative phase at specified times."""
        self.utime = None
        self.time = array(time)
        self.cphase = []
        for t in time:
            shifted_param = self.param.copy()
            shifted_param[0] -= t.jd
            polynomial = Polynomial(shifted_param)
            roots = polynomial.roots()
            assert len(roots) == 1
            self.cphase.extend(roots)
