def get_fn(receiver, name):
    fn = getattr(receiver, name)
    if not callable(fn):
        raise TypeError(
            f"Expected {receiver}.{name} to be function, found "
            f"{type(fn)}: {fn}"
        )
    return fn

if __name__ == "__main__":
    import doctest
    doctest.testmod()
