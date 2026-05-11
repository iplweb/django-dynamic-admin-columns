import sys


def qual(clazz):
    """
    Return full import path of a class.

    Function stolen from twisted.python.reflect!
    """
    return clazz.__module__ + "." + clazz.__name__


def str_to_class(path):
    """Return a class from a string representation"""
    split = path.split(".")
    module = ".".join(split[:-1])
    field = split[-1]

    try:
        identifier = getattr(sys.modules[module], field)
    except AttributeError as exc:
        raise NameError(f"{field} doesn't exist.") from exc
    return identifier
