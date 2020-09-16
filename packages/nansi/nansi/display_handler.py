import logging
from ansible.utils.display import Display

class DisplayHandler(logging.Handler):
    '''
    A handler class that writes messages to Ansible's
    `ansible.utils.display.Display`, which then writes them to the user output.
    '''
    
    def __init__(self, display=None):
        logging.Handler.__init__(self)

        if display is None:
            display = Display()
        
        self.display = display
    # #__init__


    def emit(self, record):
        '''
        Overridden to send log records to Ansible's display.
        '''

        if self.display is None:
            # Nothing we can do, drop it
            return

        try:
            self.format(record)

            if record.levelname == 'DEBUG':
                return self.display.verbose(record.message, caplevel=1)

            elif record.levelname == 'INFO':
                return self.display.verbose(record.message, caplevel=0)

            elif record.levelname == 'WARNING':
                self.display.warning(record.message)

            elif record.levelname == 'ERROR':
                self.display.error(record.message)

            elif record.levelname == 'CRITICAL':
                self.display.error("(CRITICAL) {}".format(record.message))

            else:
                pass
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            raise
            # self.handleError(record)
    # #emit