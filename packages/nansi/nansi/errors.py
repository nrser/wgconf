from nansi.utils.strings import coordinate

class ArgTypeError(TypeError):
    def __init__(self, arg_name, expected, given):
        super().__init__(
            f"Expected `{arg_name}` to be {coordinate(expected, 'or')}, given "
            f"{type(given)}: {repr(given)}"
        )
