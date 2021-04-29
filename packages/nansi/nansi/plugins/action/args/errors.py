class CastTypeError(TypeError):
    # def __init__(self, *args, **kwds):
    #     args_map = dict(zip(["message", "expected", "given"], args))
    #     dups = set(args_map).intersection(kwds)

    #     if len(dups) != 0:
    #         raise TypeError(
    #             f"CastError() got multiple values for arguments {dups}"
    #         )

    #     args_map.update(kwds)
    #     self.expected = args_map["expected"]
    #     self.given = args_map["given"]

    #     if "message" not in args_map:
    #         args_map["message"] = (
    #             f"Expected a {self.expected}, "
    #             f"given a {type(self.given)}: {self.given}"
    #         )

    #     super().__init__(args_map["message"])

    def __init__(self, message, arg, value):
        super().__init__(message)
        self.arg = arg
        self.value = value

class CastValueError(ValueError):
    def __init__(self, message, arg, value):
        super().__init__(message)
        self.arg = arg
        self.value = value
