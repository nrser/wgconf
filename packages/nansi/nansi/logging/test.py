import logging

from rich import box
from rich.table import Table
from rich.highlighter import ReprHighlighter
from rich.pretty import Pretty
from rich.text import Text

LOG = logging.getLogger(__name__)

def V(**values):
    table = Table(
        show_header=False,
        title=None,
        # box=box.MINIMAL,
        box=None,
        # border_style="blue",
    )
    highlighter = ReprHighlighter()
    # for key, value in values.items():
    #     table.add_row(
    #         key, "=", Pretty(value, highlighter=highlighter)
    #     )
    for key, value in values.items():
        # key_text = Text.assemble(
        #     (key, "scope.key.special" if key.startswith("__") else "scope.key"),
        #     (" =", "scope.equals"),
        # )
        table.add_row(
            Text(key, "scope.key.special" if key.startswith("__") else "scope.key"),
            Text(" =", "scope.equals"),
            Pretty(value, highlighter=highlighter),
        )
    return table

def test_logger(log=LOG):
    test_data = [
        {"jsonrpc": "2.0", "method": "sum", "params": [None, 1, 2, 4, False, True], "id": "1",},
        {"jsonrpc": "2.0", "method": "notify_hello", "params": [7]},
        {"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": "2"},
    ]
    
    for method in (
        name.lower()
        for name in logging._levelToName.values()
        if name not in ('NOTSET',) # 'DEBUG', 'INFO', 'WARNING')
    ):
        fn = getattr(log, method)
        fn("A message...", V(plus_some='values', i_wanna={'log': 'TOO!'}))
        fn("A data...", test_data)
    
    for msg in (
        "Hi my name is mica and i like to cook pot brownies with cheese.",
        "Hudie is my favorite friend in the world and she is fuzzy and warm.",
        "The other day I went for a walk down to the sea and ate some fish. " +
        "A second instead of first is better than last in the end no one " +
        "really cares too much",
    ):
        log.info(msg)

