import yaml
from rich.console import Console
from os.path import dirname

C = Console()

with open(f"{dirname(__file__)}/state_mate.yaml", 'r') as f:
    parse = yaml.safe_load(f)

C.print(parse)
