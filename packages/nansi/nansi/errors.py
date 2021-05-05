from nansi.utils.strings import coord

class ArgTypeError(TypeError):
    def __init__(self, arg_name, expected, given):
        super().__init__(
            f"Expected `{arg_name}` to be {coord(expected, 'or')}, given "
            f"{type(given)}: {repr(given)}"
        )
