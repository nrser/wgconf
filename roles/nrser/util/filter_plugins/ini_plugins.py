def ini_enc_value(value):
    """Encode `value` for use in the `ini_file` module's `value:` parameter.
    """
    if value is True:
        return 'yes'
    elif value is False:
        return 'no'
    else:
        return value

class FilterModule:
    def filters(self):
        return dict(
            ini_enc_value=ini_enc_value,
        )
    