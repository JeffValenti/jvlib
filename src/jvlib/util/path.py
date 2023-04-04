from collections.abc import Iterable
from pathlib import Path

def pathlist(pathspec):
    '''Resolve path specification into explicit list of Path obects.

    Check that input path specification is str, Path object, or iterable
    containing str and/or Path objects.
    Expand each input str or Path with Path.glob() and Path.expanduser().
    Check that every file and/or directory in final path list all exist.
    Sort and remove duplicates in final path list.
    '''
    if isinstance(pathspec, (str, Path)):
        pathspec = [pathspec]
    else:
        try:
            pathspec = list(pathspec)
            assert all([isinstance(spec, (str, Path)) for spec in pathspec])
        except (TypeError, AssertionError):
            raise ValueError(f'pathspec must consist of str and/or Path')
    pathlist = []
    for spec in pathspec:
        path = Path(spec).expanduser()
        if path.is_absolute():
            parent = path.parent
        else:
            parent = Path('.')
        try:
            assert parent.exists()
        except AssertionError as e:
            raise ValueError(f'directory not found: {parent}')
        pathlist.extend(parent.glob(path.name))
    pathlist = sorted(set(pathlist))
    for path in pathlist:
        try:
            assert path.exists()
        except AssertionError as e:
            raise ValueError(f'file not found: {path}')
    return pathlist
