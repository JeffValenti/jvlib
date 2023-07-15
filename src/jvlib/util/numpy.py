from numpy import inf, printoptions


def print_all(array):
    '''Print all elements in numpy array. Preserve numpy print options.'''
    with printoptions(threshold=inf):
        print(array)
