import logging

class KwdsLogger(logging.getLoggerClass()):
    def _log(
        self,
        level,
        msg,
        args,
        exc_info=None,
        extra=None,
        stack_info=False,
        **data,
    ):
        """
        Low-level log implementation, proxied to allow nested logger adapters.
        """

        if extra is not None:
            if isinstance(extra, dict):
                extra = {'data': data, **extra}
        else:
            extra = {'data': data}

        super()._log(
            level,
            msg,
            args,
            exc_info=exc_info,
            stack_info=stack_info,
            extra=extra,
        )