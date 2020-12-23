import logging

class LogRecord(logging.LogRecord):
    def getMessage(self) -> str:
        try:
            return super().getMessage()
        except TypeError:
            return str(self.msg)
