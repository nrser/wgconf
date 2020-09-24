import logging

class LogRecord(logging.LogRecord):    
    def getMessage(self) -> str:
        try:
            return super().getMessage()
        except TypeError as error:
            return str(self.msg)
