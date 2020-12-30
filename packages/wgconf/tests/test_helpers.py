import pathlib

TESTS_DIR = pathlib.Path(__file__).parent.absolute()
DATA_DIR = TESTS_DIR / 'test_data'

def unblock(block: str) -> str:
    lines = [l.lstrip() for l in block.split('\n')]
    if lines[0] == '':
        del lines[0]
    if lines[-1] == '' and lines[-2] == '':
        del lines[-1]
    return ''.join((f"{l}\n" for l in lines))


def data_path(*segments):
    return DATA_DIR.join(*segments)
