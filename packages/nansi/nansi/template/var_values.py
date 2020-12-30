from collections.abc import Mapping

class VarValues(Mapping):
    def __init__(self, templar, task_vars):
        self.templar = templar
        self.raw = task_vars

    def __getitem__(self, key):
        return self.templar.template(self.raw[key])

    def __iter__(self):
        return iter(self.raw)

    def __len__(self):
        return len(self.raw)

    def __contains__(self, key):
        return key in self.raw

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and other.raw == self.raw
            and other.templar == self.templar
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default

    def keys(self):
        return self.raw.keys()

    def values(self):
        '''Iteration by values is not supported -- raises `RuntimeError`.

        This is both because:

        1.  It's expensive -- would render *every* variable, and there are
            a *lot*.

        2.  I don't feel like there is any contract in Ansibland, explicit or
            implied, that says all variables *must* be renderable at all times,
            even if they are never going to be used.
        '''
        raise RuntimeError(
            f"{self.__class__} does not support iteration by value.\n\n" +
            "This is because it renders values from source variables on,\n" +
            "demand, and there's usually a *lot* of variables, some of\n" +
            "which may not be renderable if they were never going to be used."
        )

    def items(self):
        '''Iteration with values is not supported -- raises `RuntimeError`.

        This is both because:

        1.  It's expensive -- would render *every* variable, and there are
            a *lot*.

        2.  I don't feel like there is any contract in Ansibland, explicit or
            implied, that says all variables *must* be renderable at all times,
            even if they are never going to be used.
        '''
        raise RuntimeError(
            f"{self.__class__} does not support iteration by value.\n\n" +
            "This is because it renders values from source variables on,\n" +
            "demand, and there's usually a *lot* of variables, some of\n" +
            "which may not be renderable if they were never going to be used."
        )
