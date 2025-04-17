from __future__ import annotations
from typing import (
    Any,
    TYPE_CHECKING,
)

import pathlib
import re
import shlex

from poetry.core.packages import dependency as poetry_dep

from metapkg import packages
from metapkg import targets

from edgedbpkg import postgresql

if TYPE_CHECKING:
    from cleo.io import io as cleo_io


class PostgresCExtension(packages.BundledCAutoconfPackage):
    # Populated in resolve() when this is built as top-level package.
    bundle_deps: list[packages.BundledPackage] = []
    _pg: postgresql.PostgreSQL

    @classmethod
    def resolve(
        cls,
        io: cleo_io.IO,
        *,
        name: packages.NormalizedName | None = None,
        version: str | None = None,
        revision: str | None = None,
        is_release: bool = False,
        target: targets.Target,
        requires: list[poetry_dep.Dependency] | None = None,
    ) -> PostgresCExtension:
        slot: str | None = None
        if version is not None:
            slot, _, version = version.rpartition("!")

        if not slot:
            raise RuntimeError(
                "must specify PostgreSQL major version as epoch, eg 16!4.0.0"
            )

        pg_ver = slot
        if "." not in pg_ver:
            pg_ver = f"{pg_ver}.0"

        pg = postgresql.PostgreSQL(version=pg_ver)

        ext = super().resolve(
            io,
            version=version,
            revision=revision,
            is_release=is_release,
            target=target,
            requires=requires,
        )

        ext.bundle_deps.append(pg)
        ext.build_requires.append(pg.to_dependency())
        ext._pg = pg

        if slot is not None:
            ext.set_slot(str(slot))

        return ext

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._slot = ""

    def set_slot(self, slot: str) -> None:
        self._slot = slot

    @property
    def slot(self) -> str:
        return self._slot

    def version_includes_slot(self) -> bool:
        return False

    @property
    def supports_out_of_tree_builds(self) -> bool:
        return True

    def get_configure_script(self, build: targets.Build) -> str:
        source = build.get_source_dir(self, relative_to="pkgbuild")
        return (
            f"if [ -x {shlex.quote(str(source))}/configure ]; then\n"
            + super().get_configure_script(build)
            + "\nfi\n"
        )

    def get_configure_args(
        self,
        build: targets.Build,
        wd: str | None = None,
    ) -> packages.Args:
        if wd is None:
            wd = "$(pwd -P)"
        pg_config = f'{wd}/{build.sh_get_command("pg_config")}'
        return super().get_configure_args(build, wd=wd) | {
            "PG_CONFIG": f"!{pg_config}",
        }

    def get_build_env(
        self, build: targets.Build, wd: str | None
    ) -> packages.Args:
        pg_config = f'{wd}/{build.sh_get_command("pg_config")}'
        return super().get_build_env(build, wd=wd) | {
            "PG_CONFIG": f"!{pg_config}",
            "USE_PGXS": "1",
        }

    def get_build_install_env(
        self, build: targets.Build, wd: str
    ) -> packages.Args:
        pg_config = f'{wd}/{build.sh_get_command("pg_config_install")}'
        return super().get_build_install_env(build, wd=wd) | {
            "PG_CONFIG": f"!{pg_config}",
            "USE_PGXS": "1",
        }

    def get_patches(self) -> dict[str, list[tuple[str, str]]]:
        v = f"{self.version.major}{self.version.minor:02}"

        patches = dict(super().get_patches())
        for pkg, pkg_patches in patches.items():
            if pkg == self.name:
                filtered = []
                for i, (pn, pfile) in enumerate(list(pkg_patches)):
                    m = re.match(r"^.*-(\d+)$", pn)
                    if m and m.group(1) != v:
                        pass
                    else:
                        filtered.append((pn, pfile))
                patches[pkg] = filtered
                break

        return patches

    def get_root_install_subdir(self, build: targets.Build) -> pathlib.Path:
        return pathlib.Path(self._pg.name_slot)

    def get_dep_install_subdir(
        self,
        build: targets.Build,
        pkg: packages.BasePackage,
    ) -> pathlib.Path:
        prefix = build.get_install_prefix(self)
        lib_dir = build.get_install_path(self, "lib").relative_to(prefix)
        if pkg.name != "postgresql-edgedb":
            return lib_dir / "postgresql" / pathlib.Path(self.unique_name)
        else:
            return pathlib.Path("")
