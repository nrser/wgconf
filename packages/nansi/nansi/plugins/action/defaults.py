from types import MappingProxyType

APT_DEFAULTS = MappingProxyType(dict(
    # This makes sense to always have when coupled with `cache_valid_time`,
    # which prevents the update from happening on *every* *fucking* *run*
    update_cache        = True,
    # Only actually update ever 24 hours (value in seconds)
    cache_valid_time    = (24 * 60 * 60),
    # In order to remove config files
    purge               = True,
    # autoremove is also a consideration, but seems like it's independent of
    # state and full-system..?
))
