from collections.abc import Mapping

def test_task_args(value) -> bool:
    return value is True or isinstance(value, Mapping)

def to_task_args(value) -> Mapping:
    if value is True:
        return {}
    elif isinstance(value, Mapping):
        return value
    raise TypeError(f"Expected True or Mapping, got {type(value)}")

class FilterModule:
    def filters(self):
        return dict(
            test_task_args=test_task_args,
            to_task_args=to_task_args,
        )

if __name__ == '__main__':
    import doctest
    doctest.testmod()
