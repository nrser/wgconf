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

class A:
    def __init__(self, x):
        self.x = x

    @lazy_property
    def y(self):
        print("Computing y...")
        return f"x is {self.x}"

a = A("blah")

print(f"1.  {a.y}")
print(f"2.  {a.y}")
print(f"3.  {a.y}")

print(a.__dict__)