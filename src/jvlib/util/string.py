from math import floor, log10


def digits_after_decimal(uncertainty, nsigfig=2):
    """Return number of digits to print after decimal."""
    return nsigfig - floor(log10(uncertainty)) - 1

def sigma_pm(value, sigma, nsigfig=2, nspace=1):
    """Return string with value plus or minus sigma."""
    space = ' ' * nspace
    ndigit = digits_after_decimal(sigma, nsigfig=nsigfig)
    print(ndigit)
    if ndigit >= 0:
        return f"{value:.{ndigit}f}{space}±{space}{sigma:.{ndigit}f}"
    else:
        return f"{value:.{ndigit}e}{space}±{space}{sigma:.{ndigit}e}"
        scale = 10**ndigit
        print(scale)
        value_str = f"{scale * value:.0f}"
        sigma_str = f"{scale * sigma:.0f}"
        return f"({value_str}{space}±{space}{sigma_str}){space}e+{-ndigit}"
