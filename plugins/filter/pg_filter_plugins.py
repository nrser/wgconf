def splat(f):
    return lambda seq: f(*seq)

def dictsplat(f):
    return lambda dct: f(**dct)

def pg_deb_pkg_list(
    pg_version,
    pg_client,
    pg_contrib,
    pg_frontend_dev,
    pg_backend_dev,
):
    if int(pg_version) >= 10 and int(pg_version) != float(pg_version):
        raise RuntimeError(
            "For postgres 10+ only major versions should be provided " +
            f"({int(pg_version)} instead of {pg_version}"
        )

    pkgs = [f"postgresql-{pg_version}"]

    if pg_client:
        pkgs.append(f"postgresql-client-{pg_version}")
    if pg_contrib and int(pg_version) < 10:
        pkgs.append(f"postgresql-contrib-{pg_version}")
    if pg_frontend_dev:
        pkgs.append("libpq-dev")
    if pg_backend_dev:
        pkgs.append(f"postgresql-server-dev-{pg_version}")

    return pkgs

class FilterModule:
    def filters(self):
        return dict(
            pg_deb_pkg_list=splat(pg_deb_pkg_list),
        )
