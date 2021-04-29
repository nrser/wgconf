from functools import wraps

def lazy_property(fn):
    attr_name = f"_{fn.__name__}"
    @wraps(fn)
    def lazy_wrapper(instance):
        if hasattr(instance, attr_name):
            return getattr(instance, attr_name)
        value = fn(instance)
        setattr(instance, attr_name, value)
        return value
    return property(lazy_wrapper)
