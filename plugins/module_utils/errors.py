class FailError(Exception):
    def __init__(self, msg, **kwds):
        super().__init__(msg)
        self.msg = msg
        for name, value in kwds.items():
            setattr(self, name, value)

    def fail_kwds(self):
        return self.__dict__
