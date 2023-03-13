def use_or_set_default(obj, default):
    """Return default if obj is None, else set default and return obj."""
    if obj is None:
        return default
    else:
        default = obj
        return obj
