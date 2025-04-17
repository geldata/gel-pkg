from __future__ import annotations

import pathlib
import platform
import re
import shlex
import textwrap

from poetry.core.constraints import version as poetry_version

from metapkg import packages
from metapkg import targets

from edgedbpkg import libb2
from edgedbpkg import libffi
from edgedbpkg import libuuid
from edgedbpkg import openssl
from edgedbpkg import zlib


class Python(packages.BundledCAutoconfPackage):
    title = "Python"
    ident = "python-edgedb"

    _pftp = "https://www.python.org/ftp/python/{base_version}/"

    sources = [
        {
            "url": _pftp + "Python-{version}.tgz",
        }
    ]

    artifact_requirements = [
        "openssl (>=1.1.1)",
        "libb2 (>=0.98.1)",
        "libffi (>=3.0.13)",
        "uuid",
        "zlib",
    ]

    artifact_build_requirements = [
        "libb2-dev (>=0.98.1)",
        "libffi-dev (>=3.0.13)",
        "openssl-dev (>=1.1.1)",
        "uuid-dev",
        "zlib-dev",
    ]

    bundle_deps = [
        openssl.OpenSSL("3.3.1"),
        libb2.LibB2("0.98.1"),
        libffi.LibFFI("3.4.6"),
        libuuid.LibUUID("2.39.3"),
        zlib.Zlib("1.3.1"),
    ]

    @classmethod
    def get_source_url_variables(cls, version: str) -> dict[str, str]:
        base_ver = poetry_version.Version.parse(version).release.to_string()
        return {
            "base_version": base_ver,
        }

    def get_patches(self) -> dict[str, list[tuple[str, str]]]:
        v = f"{self.version.major}{self.version.minor}"

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

    def get_configure_env(
        self,
        build: targets.Build,
        wd: str | None = None,
    ) -> packages.Args:
        env_args = dict(super().get_configure_env(build, wd=wd))
        if build.target.libc == "musl":
            # Set explicit stack size on musl where the default is too
            # low to support the default recursion limit.
            # See https://github.com/python/cpython/issues/76488
            build.sh_append_flags(
                env_args,
                "LDFLAGS",
                ("-Wl,-z,stack-size=1000000",),
            )
        return env_args

    def get_configure_args(
        self,
        build: targets.Build,
        wd: str | None = None,
    ) -> packages.Args:
        conf_args = super().get_configure_args(build, wd=wd) | {
            "--enable-ipv6": None,
            "--with-dbmliborder": "bdb:gdbm",
            "--with-computed-gotos": None,
        }

        if build.extra_optimizations_enabled():
            if build.supports_pgo():
                conf_args["--enable-optimizations"] = None
            if build.supports_lto():
                conf_args["--with-lto"] = None
            if build.uses_modern_gcc():
                build.sh_append_flags(
                    conf_args,
                    "CFLAGS",
                    ("-fno-semantic-interposition",),
                )

        if platform.system() == "Darwin":
            conf_args["--enable-universalsdk"] = "!$(xcrun --show-sdk-path)"
            arch = build.target.machine_architecture
            if arch == "x86_64":
                conf_args["--with-universal-archs"] = "intel-64"
            elif arch == "aarch64":
                conf_args["--with-universal-archs"] = "arm-64"
            else:
                raise RuntimeError(f"unexpected architecture: {arch}")

        libffi_pkg = build.get_package("libffi")
        if not build.is_bundled(libffi_pkg):
            # This is somewhat confusing, but Python treats
            # --without-system-ffi on macOS as instruction to actually
            # _use_ the native system libffi (as opposed to pkg-config),
            # and ignores this option on other platforms.
            conf_args["--without-system-ffi"] = None

        openssl_pkg = build.get_package("openssl")
        if build.is_bundled(openssl_pkg):
            build.sh_replace_quoted_paths(
                conf_args,
                "--with-openssl",
                build.sh_get_bundled_install_path(openssl_pkg, wd=wd),
            )
            build.sh_replace_paths(
                conf_args,
                "--with-openssl-rpath",
                build.get_install_path(openssl_pkg, "lib"),
            )

        return conf_args

    def get_build_script(self, build: targets.Build) -> str:
        prefix = build.get_rel_install_prefix(self)
        dest = build.get_temp_root(relative_to="pkgbuild")

        if platform.system() == "Darwin":
            exe_suffix = ".exe"
        else:
            exe_suffix = ""

        sitescript = (
            "import site; import pathlib; "
            "print(pathlib.Path( "
            'site.getsitepackages([\\"${p}\\"])[0]).resolve())'
        )

        python = f"python{exe_suffix}"

        wrapper_env_args = dict(self.get_ld_env(build, wd="${d}"))

        openssl_pkg = build.get_package("openssl")
        if build.is_bundled(openssl_pkg):
            ssl_inst_dir = build.get_build_install_dir(
                openssl_pkg, relative_to="pkgbuild"
            )
            ssldir = build.get_install_path(openssl_pkg, "sysconf") / "ssl"
            cacert = ssl_inst_dir / ssldir.relative_to("/") / "cert.pem"
            build.sh_replace_quoted_paths(
                wrapper_env_args,
                "SSL_CERT_FILE",
                [f'"${{d}}"/{shlex.quote(str(cacert))}'],
            )

        wrapper_env = build.sh_format_args(
            wrapper_env_args,
            force_args_eq=True,
            linebreaks=False,
        )
        bash = build.sh_get_command("bash")

        make_wrapper = textwrap.dedent(
            f"""\
            echo '#!{bash}' > python-wrapper
            echo set -Exe -o pipefail >> python-wrapper
            echo 'd=$(cd -- "$(dirname "$0")" >/dev/null 2>&1; pwd -P)' \\
                >> python-wrapper
            echo 'unset __PYVENV_LAUNCHER__' >> python-wrapper
            {f"echo 'export {wrapper_env}' >> python-wrapper"
             if wrapper_env else ""}
            echo 'p=${{d}}/{dest}/{prefix}' >> python-wrapper
            echo 's=$(${{d}}/{python} -c "{sitescript}")' >> python-wrapper
            echo export PYTHONPATH='${{s}}':"${{EXTRA_PYTHONPATH}}" \\
                >> python-wrapper
            echo exec '${{d}}/{python}' '"$@"' >> python-wrapper
            chmod +x python-wrapper
            cat python-wrapper
        """
        )

        disabled_modules = [
            "_sqlite3",
            "_tkinter",
            "_dbm",
            "_gdbm",
            "_lzma",
            "_bz2",
            "_curses",
            "_curses_panel",
            "_crypt",
            "audioop",
            "readline",
            "nis",
            "ossaudiodev",
            "spwd",
        ]

        make = self.get_build_command(build, self.get_make_args(build))

        return textwrap.dedent(
            f"""\
            # make sure no funny business is going on if metapkg
            # is ran from a venv.
            unset __PYVENV_LAUNCHER__
            echo '*disabled*' >> Modules/Setup.local
            echo '' >> Modules/Setup.local
            echo {' '.join(disabled_modules)} >> Modules/Setup.local
            # make sure config.c is regenerated reliably by make
            rm Modules/config.c
            ls -al Modules/
            _wd=$(pwd -P)
            {make}
            ./{python} -m ensurepip --root "{dest}"
            {make_wrapper}"""
        )

    def get_build_install_env(
        self, build: targets.Build, wd: str
    ) -> packages.Args:
        return super().get_build_install_env(build, wd=wd) | {
            "ENSUREPIP": "no",
        }

    def get_make_install_args(
        self,
        build: targets.Build,
    ) -> packages.Args:
        # Python's make install isn't thread-safe
        return super().get_make_args(build) | {"-j1": None}

    def get_build_install_script(self, build: targets.Build) -> str:
        script = super().get_build_install_script(build)
        installdest = build.get_build_install_dir(self, relative_to="pkgbuild")

        bin_dir = build.get_install_path(self, "bin")
        minorv = self.version.minor
        extra_install = textwrap.dedent(
            f"""\
            rm $(pwd)/"{installdest}"/"{bin_dir}"/python3
            mv $(pwd)/"{installdest}"/"{bin_dir}"/python3.{minorv} \
                $(pwd)/"{installdest}"/"{bin_dir}"/python3
            """
        )

        script += textwrap.dedent(
            f"""\
            {extra_install}
            """
        )

        return script

    def get_build_tools(self, build: targets.Build) -> dict[str, pathlib.Path]:
        build_dir = build.get_build_dir(self)
        return {"python": build_dir / "python-wrapper"}
