import numpy as np


def densest_cluster_mean(array, npix):
    '''Calculate mean of densest cluster of values in 1D array.

    Parameters
    ----------
    array : numpy.ndarray
        One-dimensional array of values.
    npix : int
        Number of pixels to include in clusters.

    Returns
    -------
    dcm : float
        Mean of densest cluster of values.
    diff : float
        Maximum value minus minimum value in cluster used to compute dcm.
    '''
    index = npix - 1
    sarr = sorted(array)
    diffs = [v2 - v1 for v2, v1 in zip(sarr[npix-1:], sarr[:-npix+1])]
    imin = np.argmin(diffs)
    diff = diffs[imin]
    dcm = np.mean(sarr[imin:imin+npix])
    return dcm, diff


def background_dcm(image, axis, npix):
    '''Calculate densest cluster mean for slices along specified axis.

    Parameters
    ----------
    image : numpy.ndarray
        Two-dimensional image of a scene.
    axis : int
        Axis along which mean is computed.
    npix : int
        Number of pixels to include in clusters.

    Returns
    -------
    means : numpy.ndarray
        Mean of densest cluster for each column (axis=0) or row (axis=1).
    diffs : numpy.ndarray
        Maximum value minus minimum value in clusters used to compute means.
    '''
    means, diffs = np.apply_along_axis(
        densest_cluster_mean, axis, image, npix)
    return means, diffs

