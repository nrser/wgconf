from pathlib import Path

def get__DIR__(file):
    return Path(__file__).parent.absolute()
