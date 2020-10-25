def unblock(block: str) -> str:
    lines = [l.lstrip() for l in block.split('\n')]
    if lines[0] == '':
        del lines[0]
    if lines[-1] == '' and lines[-2] == '':
        del lines[-1]
    return ''.join((f"{l}\n" for l in lines))
    