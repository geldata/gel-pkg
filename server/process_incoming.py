#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, ContextManager, cast, List, Optional
from typing_extensions import TypedDict

import contextlib
import datetime
import hashlib
import fnmatch
import functools
import io
import json
import os
import logging
import mimetypes
import pathlib
import pprint
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import textwrap

import boto3
import boto3.session
import click
import filelock
import semver
import tomli

from debian import debian_support

import mypy_boto3_s3
from mypy_boto3_s3 import type_defs as s3types
from mypy_boto3_s3 import service_resource as s3


CACHE = "Cache-Control:public, no-transform, max-age=315360000"
NO_CACHE = "Cache-Control:no-store, no-cache, private, max-age=0"
ARCHIVE = pathlib.Path("archive")
DIST = pathlib.Path("dist")

logging.basicConfig(format="%(message)s")
logger = logging.getLogger("process_incoming")
logger.setLevel(logging.INFO)


class CommonConfig(TypedDict):
    signing_key: str
    buckets: dict[str, str]


class GenericConfig(TypedDict):
    pass


class DistroDescription(TypedDict):
    codename: str
    name: str


class APTConfig(TypedDict):
    architectures: list[str]
    components: list[str]
    distributions: list[DistroDescription]


class RPMConfig(TypedDict):
    pass


class Config(TypedDict):
    common: CommonConfig
    generic: GenericConfig
    apt: APTConfig
    rpm: RPMConfig


class Prerelease(TypedDict):
    phase: str
    number: int


class Version(TypedDict):
    major: int
    minor: int | None
    patch: int | None
    prerelease: list[Prerelease]
    metadata: dict[str, str]


slot_regexp = re.compile(
    r"^(\w+(?:-[a-zA-Z]*)*?)"
    + r"(?:-(\d+(?:-(?:alpha|beta|rc)\d+)?(?:-dev\d+)?))?$",
    re.A,
)


version_regexp = re.compile(
    r"""^
    (?P<release>[0-9]+(?:\.[0-9]+)*)
    (?P<pre>
        [-]?
        (?P<pre_l>(a|b|c|rc|alpha|beta|pre|preview))
        [\.]?
        (?P<pre_n>[0-9]+)?
    )?
    (?P<dev>
        [\.-]?
        (?P<dev_l>dev)
        [\.]?
        (?P<dev_n>[0-9]+)?
    )?
    (?:\+(?P<local>[a-z0-9]+(?:[\.][a-z0-9]+)*))?
    $""",
    re.X | re.A,
)


def subprocess_run(
    *args: Any, **kwargs: Any
) -> subprocess.CompletedProcess[str]:
    kw = dict(kwargs)
    if kw.get("stdout") is None and not kw.get("capture_output"):
        kw["stdout"] = sys.stderr
    return subprocess.run(*args, **kw)


def parse_version(ver: str) -> Version:
    v = version_regexp.match(ver)
    if v is None:
        raise ValueError(f"cannot parse version: {ver}")

    prerelease: list[Prerelease] = []

    if v.group("pre"):
        pre_l = v.group("pre_l")
        if pre_l in {"a", "alpha"}:
            pre_kind = "alpha"
        elif pre_l in {"b", "beta"}:
            pre_kind = "beta"
        elif pre_l in {"c", "rc"}:
            pre_kind = "rc"
        else:
            raise ValueError(f"cannot determine release stage from {ver}")

        prerelease.append({"phase": pre_kind, "number": int(v.group("pre_n"))})
        if v.group("dev"):
            prerelease.append(
                {"phase": "dev", "number": int(v.group("dev_n"))}
            )

    elif v.group("dev"):
        prerelease.append({"phase": "dev", "number": int(v.group("dev_n"))})

    metadata = {}
    if v.group("local"):
        for segment in v.group("local").split("."):
            if segment[0] == "d":
                field = "source_date"
                value = segment[1:]
            elif segment[0] == "g":
                field = "scm_revision"
                value = segment[1:]
            elif segment[:2] == "cv":
                field = "catalog_version"
                value = segment[2:]
            else:
                continue

            metadata[field] = value

    release = [int(r) for r in v.group("release").split(".")]

    return Version(
        major=release[0],
        minor=release[1] if len(release) == 2 else None,
        patch=release[2] if len(release) == 3 else None,
        prerelease=prerelease,
        metadata=metadata,
    )


class InstallRef(TypedDict):
    ref: str
    type: str | None
    encoding: str | None
    verification: dict[str, str | int]


class Package(TypedDict):
    basename: str  # edgedb-server
    slot: str | None  # 1-alpha6-dev5069
    name: str  # edgedb-server-1-alpha6-dev5069
    version: str  # 1.0a6.dev5069+g0839d6e8
    version_details: Version
    version_key: str  # 1.0.0~alpha.6~dev.5069.2020091300~nightly
    architecture: str  # x86_64
    revision: str  # 2020091300~nightly
    build_date: str  # 2023-12-14T21:30:16+00:00
    tags: dict[str, str]  # {extension: postgis}
    installrefs: list[InstallRef]
    installref: str


class Packages(TypedDict):
    packages: list[Package]


PackageIndex = dict[tuple[str, str, str], Package]


def gpg_detach_sign(path: pathlib.Path) -> pathlib.Path:
    logger.info("gpg_detach_sign: %s", path)
    proc = subprocess_run(
        ["gpg", "--yes", "--batch", "--detach-sign", "--armor", str(path)]
    )
    proc.check_returncode()
    asc_path = path.with_suffix(path.suffix + ".asc")
    assert asc_path.exists()
    return asc_path


def sha256(path: pathlib.Path) -> pathlib.Path:
    logger.info("sha256: %s", path)
    with open(path, "rb") as bf:
        _hash = hashlib.sha256(bf.read())
    out_path = path.with_suffix(path.suffix + ".sha256")
    with open(out_path, "w") as f:
        f.write(_hash.hexdigest())
        f.write("\n")
    return out_path


def blake2b(path: pathlib.Path) -> pathlib.Path:
    logger.info("blake2b: %s", path)
    with open(path, "rb") as bf:
        _hash = hashlib.blake2b(bf.read())
    out_path = path.with_suffix(path.suffix + ".blake2b")
    with open(out_path, "w") as f:
        f.write(_hash.hexdigest())
        f.write("\n")
    return out_path


def format_version_key(ver: Version, revision: str) -> str:
    ver_components = []
    for v in (ver["major"], ver["minor"], ver["patch"]):
        if v is None:
            break
        ver_components.append(v)
    ver_key = ".".join(str(v) for v in ver_components)
    if ver["prerelease"]:
        # Using tilde for "dev" makes it sort _before_ the equivalent
        # version without "dev" when using the GNU version sort (sort -V)
        # or debian version comparison algorithm.
        prerelease = (
            ("~" if pre["phase"] == "dev" else ".")
            + f'{pre["phase"]}.{pre["number"]}'
            for pre in ver["prerelease"]
        )
        ver_key += "~" + "".join(prerelease).lstrip(".~")
    if revision:
        ver_key += f".{revision}"
    return ver_key


def remove_old(
    bucket: s3.Bucket,
    prefix: pathlib.Path,
    keep: int,
    channel: str | None = None,
) -> None:
    logger.info("remove_old: %s %s %s %s", bucket, prefix, keep, channel)
    index: dict[
        str,
        dict[
            tuple[semver.Version, datetime.datetime],
            list[str],
        ],
    ] = {}
    prefix_str = str(prefix) + "/"
    for obj in bucket.objects.filter(Prefix=prefix_str):
        if is_metadata_object(obj.key):
            continue

        metadata = get_metadata(bucket, obj.key)
        if metadata["channel"] != channel:
            continue

        key = metadata["name"]
        verslot = metadata.get("version_slot", "")
        catver = (
            metadata["version_details"]
            .get("metadata", {})
            .get("catalog_version")
        )
        if catver:
            key = f"{key}-{catver}"
        else:
            key = f"{key}-{verslot}"

        key += f"-{metadata['architecture']}"

        ver_details = metadata["version_details"]
        version = semver.VersionInfo(
            ver_details["major"],
            ver_details["minor"],
            ver_details["patch"] or 0,
            ".".join(
                f"{p['phase']}.{p['number']}"
                for p in ver_details["prerelease"]
            ),
        )
        build_date_str = metadata.get("build_date")
        if build_date_str:
            build_date = datetime.datetime.fromisoformat(build_date_str)
        else:
            build_date = datetime.datetime.fromtimestamp(
                0, tz=datetime.timezone.utc
            )
        ver_key = (version, build_date)
        index.setdefault(key, {}).setdefault(ver_key, []).append(obj.key)

    for _, versions in index.items():
        sorted_versions = sorted(versions, reverse=True)
        for ver in sorted_versions[keep:]:
            for obj_key in versions[ver]:
                logger.info("Deleting outdated: %s", obj_key)
                bucket.objects.filter(Prefix=obj_key).delete()


def describe_installref(
    bucket: s3.Bucket,
    obj: s3.ObjectSummary,
    metadata: dict[str, Any],
) -> InstallRef:
    ref = obj.key
    if not ref.startswith("/"):
        ref = f"/{ref}"

    verification: dict[str, str | int] = {
        "size": obj.size,
        "sha256": read(bucket, f"{obj.key}.sha256").decode("utf-8").rstrip(),
        "blake2b": read(bucket, f"{obj.key}.blake2b").decode("utf-8").rstrip(),
    }

    contents = metadata["contents"]
    desc = contents[pathlib.Path(obj.key).name]

    return InstallRef(
        ref=ref,
        type=desc["type"],
        encoding=desc.get("encoding"),
        verification=verification,
    )


def is_metadata_object(key: str) -> bool:
    return key.endswith(
        (".sha256", ".blake2b", ".asc", ".metadata.json", "index.html")
    )


def get_metadata(bucket: s3.Bucket, key: str) -> dict[str, Any]:
    logger.info("read: %s", f"{key}.metadata.json")
    data = read(bucket, f"{key}.metadata.json")
    return json.loads(data.decode("utf-8"))  # type: ignore


def append_artifact(
    packages: dict[tuple[str, str, str], Package],
    metadata: dict[str, Any],
    installref: InstallRef,
) -> None:
    basename = metadata["name"]
    slot = metadata.get("version_slot", "")

    version_key = format_version_key(
        metadata["version_details"],
        metadata["revision"],
    )
    version_details = metadata["version_details"]
    tags = dict(metadata.get("tags", {}))
    tags.pop("bucket", None)
    tags.pop("buckets", None)
    index_key = (metadata["name"], version_key, metadata["architecture"])
    prev_pkg = packages.get(index_key)
    if prev_pkg is not None:
        for ref in prev_pkg["installrefs"]:
            if ref["ref"] == installref["ref"]:
                break
        else:
            prev_pkg["installrefs"].append(installref)
    else:
        pkg = Package(
            basename=basename,
            name="-".join(filter(None, (basename, slot))),
            slot=slot,
            version=metadata["version"],
            version_details=version_details,
            version_key=version_key,
            revision=metadata["revision"],
            build_date=metadata.get(
                "build_date",
                "1970-01-01T00:00:00+00:00",
            ),
            tags=tags,
            architecture=metadata["architecture"],
            installref=installref["ref"],
            installrefs=[installref],
        )

        logger.info("adding %s (%s, %s) to JSON index", *index_key)
        packages[index_key] = pkg


def load_index(idxfile: pathlib.Path) -> PackageIndex:
    index: PackageIndex = {}
    if idxfile.exists():
        with open(idxfile, "r") as f:
            data = json.load(f)
            if isinstance(data, dict) and (pkglist := data.get("packages")):
                for pkg in pkglist:
                    index_key = (
                        pkg["basename"],
                        pkg["version_key"],
                        pkg["architecture"],
                    )
                    if "tags" not in pkg:
                        pkg["tags"] = {}
                    index[index_key] = Package(**pkg)  # type: ignore

    return index


def make_generic_index(
    bucket: s3.Bucket,
    prefix: pathlib.Path,
    pkg_dir: str,
) -> None:
    logger.info("make_index: %s %s %s", bucket, prefix, pkg_dir)
    packages: dict[tuple[str, str, str], Package] = {}
    for obj in bucket.objects.filter(Prefix=str(prefix / pkg_dir)):
        path = pathlib.Path(obj.key)
        leaf = path.name

        if path.parent.name != pkg_dir:
            logger.warning(f"{leaf}: wrong dist")
            continue

        if is_metadata_object(obj.key):
            logger.info(f"{leaf} is metadata")
            continue

        metadata = get_metadata(bucket, obj.key)
        installref = describe_installref(bucket, obj, metadata)
        append_artifact(packages, metadata, installref)

    index = Packages(packages=list(packages.values()))
    source_bytes = json.dumps(index).encode("utf8")
    target_dir = prefix / ".jsonindexes"
    index_name = pkg_dir + ".json"
    put(bucket, source_bytes, target_dir, name=index_name)


def put(
    bucket: s3.Bucket,
    source: pathlib.Path | bytes,
    target: pathlib.Path,  # directory
    *,
    name: str = "",
    cache: bool = False,
    content_type: str = "",
) -> s3.Object:
    ctx: ContextManager[Any]

    if isinstance(source, pathlib.Path):
        ctx = open(source, "rb")
        name = name or source.name
    elif not name:
        raise ValueError(f"Name not given for target {target}")
    else:
        ctx = contextlib.nullcontext(source)

    if not content_type:
        ct, _ = mimetypes.guess_type(name)
        if ct is not None and "/" in ct:
            content_type = ct
    logger.info("put s3://%s/%s/%s", bucket.name, target, name)
    with ctx as body:
        result = bucket.put_object(
            Key=str(target / name),
            Body=body,
            CacheControl=CACHE if cache else NO_CACHE,
            ContentType=content_type,
        )
    logger.info(result)
    return result


def read(
    bucket: s3.Bucket,
    name: str,
) -> bytes:
    f = io.BytesIO()
    bucket.download_fileobj(Key=name, Fileobj=f)
    return f.getvalue()


def sync_to_local(
    bucket: s3.Bucket,
    source: pathlib.Path,
    target: pathlib.Path,
    *,
    delete: bool = True,
    exact_timestamps: bool = False,
) -> None:
    cmd = ["aws", "s3", "sync", "--no-progress"]
    if delete:
        cmd.append("--delete")
    if exact_timestamps:
        cmd.append("--exact-timestamps")
    src_path = str(source)
    if not src_path.startswith("/"):
        src_path = f"/{src_path}"
    cmd.append(f"s3://{bucket.name}{src_path}")
    cmd.append(str(target))
    subprocess_run(cmd, check=True)


def sync_to_s3(
    bucket: s3.Bucket,
    source: pathlib.Path,
    target: pathlib.Path,
    *,
    include: str | None = None,
    exclude: str | None = None,
    delete: bool = True,
    cache_control: str = "",
) -> None:
    cmd = ["aws", "s3", "sync", "--no-progress"]
    if delete:
        cmd.append("--delete")
    if cache_control:
        cmd.extend(("--cache-control", cache_control))
    if exclude:
        cmd.extend(("--exclude", exclude))
    if include:
        cmd.extend(("--include", include))
    tgt_path = str(target)
    if not tgt_path.startswith("/"):
        tgt_path = f"/{tgt_path}"
    cmd.append(str(source))
    cmd.append(f"s3://{bucket.name}{tgt_path}")
    logger.info(" ".join(cmd))
    subprocess_run(cmd, check=True)


@click.command()
@click.option("-c", "--config", default="/etc/genrepo.toml")
@click.option("--bucket")
@click.option("--incoming-dir")
@click.option("--local-dir")
@click.argument("upload_listing")  # a single file with a listing of many files
def main(
    config: str,
    bucket: Optional[str],
    incoming_dir: str,
    local_dir: str,
    upload_listing: str,
) -> None:
    with open(config, "rb") as cf:
        cfg = cast(Config, tomli.load(cf))
        if "common" not in cfg:
            raise ValueError("missing required [common] section in config")
        if not cfg["common"].get("buckets"):
            cfg["common"]["buckets"] = {}

    if bucket:
        cfg["common"]["buckets"]["default"] = bucket

    os.chdir(incoming_dir)
    with open(upload_listing) as upload_listing_file:
        uploads = upload_listing_file.read().splitlines()
    os.unlink(upload_listing)

    region = os.environ.get("AWS_REGION", "us-east-2")
    session = boto3.session.Session(region_name=region)
    s3: mypy_boto3_s3.S3ServiceResource = session.resource(
        "s3"
    )  # pyright: ignore

    for path_str in uploads:
        path = pathlib.Path(path_str)
        if not path.is_file():
            logger.info("File not found: %s", path)
            continue
        if path.suffix != ".tar":
            logger.info("File is not a .tar archive: %s", path)
            continue

        logger.info("Looking at: %s", path)
        tmp_mgr = tempfile.TemporaryDirectory(prefix="genrepo", dir=local_dir)
        try:
            with tarfile.open(path, "r:") as tf, tmp_mgr as temp_dir:
                metadata_file = tf.extractfile("build-metadata.json")
                if metadata_file is None:
                    logger.info(
                        "Tarball does not contain 'build-metadata.json': %s",
                        path,
                    )
                    continue

                metadata = json.loads(metadata_file.read())
                repository = metadata.get("repository")

                local_dir_path = pathlib.Path(local_dir)
                temp_dir_path = pathlib.Path(temp_dir)
                lock_path = local_dir_path / f"{repository}.lock"

                tags = metadata.get("tags") or {}
                tag_buckets = []

                raw_tag_buckets = tags.get("buckets", "")
                if raw_tag_buckets:
                    tag_buckets = [
                        bucket.strip() for bucket in raw_tag_buckets.split(",")
                    ]

                if not tag_buckets:
                    tag_buckets = [tags.get("bucket", "default")]

                logger.info(f"Obtaining {lock_path}")
                with filelock.FileLock(lock_path, timeout=3600):
                    for target_bucket in tag_buckets:
                        bucket = cfg["common"]["buckets"].get(target_bucket)
                        if bucket is None:
                            raise RuntimeError(
                                f"invalid target bucket in metadata: {target_bucket!r}"
                                f", configure it in genrepo.toml"
                            )

                        if repository == "generic":
                            process_generic(
                                cfg,
                                s3,
                                tf,
                                metadata,
                                bucket,
                                temp_dir_path,
                                local_dir_path,
                            )
                        elif repository == "apt":
                            process_apt(
                                cfg,
                                s3,
                                tf,
                                metadata,
                                bucket,
                                temp_dir_path,
                                local_dir_path,
                            )
                        elif repository == "rpm":
                            process_rpm(
                                cfg,
                                s3,
                                tf,
                                metadata,
                                bucket,
                                temp_dir_path,
                                local_dir_path,
                            )

            logger.info("Successfully processed: %s", path)
        finally:
            try:
                os.unlink(path)
            except PermissionError:
                pass


def process_generic(
    cfg: Config,
    s3session: s3.S3ServiceResource,
    tf: tarfile.TarFile,
    metadata: dict[str, Any],
    bucket_name: str,
    temp_dir: pathlib.Path,
    local_dir: pathlib.Path,
) -> None:
    bucket = s3session.Bucket(bucket_name)
    pkg_directories = set()
    rrules = {}
    basename = metadata["name"]
    slot = metadata.get("version_slot")
    slot_suf = f"-{slot}" if slot else ""
    channel = metadata["channel"]
    channel_suf = f".{channel}" if channel and channel != "stable" else ""
    target = metadata["target"]
    contents = metadata["contents"]
    pkg_dir = f"{target}{channel_suf}"
    pkg_directories.add(pkg_dir)

    staging_dir = temp_dir / pkg_dir
    os.makedirs(staging_dir)

    for member in tf.getmembers():
        if member.name in {".", "build-metadata.json"}:
            continue

        leaf = pathlib.Path(member.name)
        tf.extract(member, staging_dir)

        desc = contents[member.name]
        ext = desc["suffix"]
        asc_path = gpg_detach_sign(staging_dir / leaf)
        sha256_path = sha256(staging_dir / leaf)
        blake2b_path = blake2b(staging_dir / leaf)
        metadata_path = staging_dir / f"{leaf}.metadata.json"

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        logger.info(f"metadata={metadata}")
        logger.info(f"target={target} leaf={leaf}")
        logger.info(f"basename={basename} slot={slot}")
        logger.info(f"channel={channel} pkg_dir={pkg_dir}")
        logger.info(f"ext={ext}")

        # Store the fully-qualified artifact to archive/
        archive_dir = ARCHIVE / pkg_dir
        put(bucket, staging_dir / leaf, archive_dir, cache=True)
        put(bucket, asc_path, archive_dir, cache=True)
        put(bucket, sha256_path, archive_dir, cache=True)
        put(bucket, blake2b_path, archive_dir, cache=True)
        put(bucket, metadata_path, archive_dir, cache=True)

        links = metadata.get("publish_link_to_latest")
        if links and desc.get("encoding") == "identity":
            if isinstance(links, bool):
                links = [basename]
            else:
                assert isinstance(links, list)
            for link in links:
                # And record a copy of it in the dist/ directory as an
                # unversioned key for ease of reference in download
                # scripts.  Note: the archive/ entry is cached, but the
                # dist/ entry MUST NOT be cached for obvious reasons.
                # However, we still want the benefit of CDN for it, so
                # we generate a bucket-wide redirect policy for the
                # dist/ object to point to the archive/ object.  See
                # below for details.
                target_dir = DIST / pkg_dir
                dist_name = f"{link}{slot_suf}{ext}"
                put(bucket, b"", target_dir, name=dist_name)

                asc_name = f"{dist_name}.asc"
                put(bucket, b"", target_dir, name=asc_name)

                sha_name = f"{dist_name}.sha256"
                put(bucket, b"", target_dir, name=sha_name)

                sha_name = f"{dist_name}.blake2b"
                put(bucket, b"", target_dir, name=sha_name)

                rrules[target_dir / dist_name] = archive_dir / leaf

    for pkg_dir in pkg_directories:
        remove_old(bucket, ARCHIVE / pkg_dir, keep=1, channel="nightly")
        make_generic_index(bucket, ARCHIVE, pkg_dir)

    if rrules:
        # We can't use per-object redirects, because in that case S3
        # generates the `301 Moved Permanently` response, and, adding
        # insult to injury, forgets to send the `Cache-Control` header,
        # which makes the response cacheable and useless for the purpose.
        # Luckily the "website" functionality of the bucket allows setting
        # redirection rules centrally, so that's what we do.
        #
        # The redirection rules are key prefix-based, and so we can use just
        # one redirect rule to handle both the main artifact and its
        # accompanying signature and checksum files.
        #
        # NOTE: Amazon S3 has a limitation of 50 routing rules per
        #       website configuration.
        website = s3session.BucketWebsite(bucket_name)
        existing_rrules = list(website.routing_rules)
        for src, tgt in rrules.items():
            src_key = str(src)
            tgt_key = str(tgt)
            for rule in existing_rrules:
                condition = rule.get("Condition")
                if not condition:
                    continue
                if condition.get("KeyPrefixEquals") == src_key:
                    try:
                        redirect = rule["Redirect"]
                    except KeyError:
                        redirect = rule["Redirect"] = {}

                    redirect["ReplaceKeyPrefixWith"] = tgt_key
                    redirect["HttpRedirectCode"] = "307"
                    break
            else:
                existing_rrules.append(
                    {
                        "Condition": {
                            "KeyPrefixEquals": src_key,
                        },
                        "Redirect": {
                            "HttpRedirectCode": "307",
                            "Protocol": "https",
                            "HostName": "packages.edgedb.com",
                            "ReplaceKeyPrefixWith": tgt_key,
                        },
                    }
                )

        website_config: s3types.WebsiteConfigurationTypeDef = {
            "RoutingRules": existing_rrules,
        }

        if website.error_document is not None:
            website_config["ErrorDocument"] = website.error_document

        if website.index_document is not None:
            website_config["IndexDocument"] = website.index_document

        if website.redirect_all_requests_to is not None:
            website_config["RedirectAllRequestsTo"] = (
                website.redirect_all_requests_to
            )

        logger.info("updating bucket website config:")
        pprint.pprint(website_config, stream=sys.stderr)
        website.put(WebsiteConfiguration=website_config)


def generate_reprepro_distributions(
    cfg: Config,
) -> str:
    dists = []
    for dist in cfg["apt"]["distributions"]:
        dists.append(
            textwrap.dedent(
                f"""\
                Origin: EdgeDB Open Source Project
                Label: EdgeDB
                Suite: stable
                Codename: {dist["codename"]}
                Architectures: {" ".join(cfg["apt"]["architectures"])}
                Components: {" ".join(cfg["apt"]["components"])}
                Description: EdgeDB Package Repository for {dist["name"]}
                SignWith: {cfg["common"]["signing_key"]}
                """
            )
        )

    return "\n".join(dists)


def process_apt(
    cfg: Config,
    s3session: s3.S3ServiceResource,
    tf: tarfile.TarFile,
    metadata: dict[str, Any],
    bucket_name: str,
    temp_dir: pathlib.Path,
    local_dir: pathlib.Path,
) -> None:
    bucket = s3session.Bucket(bucket_name)
    changes = None
    incoming_dir = temp_dir / "incoming"
    incoming_dir.mkdir()
    reprepro_logs = temp_dir / "reprepro-logs"
    reprepro_logs.mkdir()
    reprepro_tmp = temp_dir / "reprepro-tmp"
    reprepro_tmp.mkdir()
    reprepro_conf = temp_dir / "reprepro-conf"
    reprepro_conf.mkdir()
    local_apt_dir = local_dir / "apt"
    local_apt_dir.mkdir(parents=True, exist_ok=True)
    index_dir = local_apt_dir / ".jsonindexes"
    index_dir.mkdir(exist_ok=True)

    with open(reprepro_conf / "incoming", "wt") as f:
        dists = " ".join(d["codename"] for d in cfg["apt"]["distributions"])
        incoming = textwrap.dedent(
            f"""\
            Name: default
            IncomingDir: {str(incoming_dir)}
            TempDir: {str(reprepro_tmp)}
            Allow: {dists}
            Permit: older_version
            """
        )
        f.write(incoming)

    with open(reprepro_conf / "distributions", "wt") as f:
        distributions = generate_reprepro_distributions(cfg)
        f.write(distributions)

    for member in tf.getmembers():
        if member.name in {".", "build-metadata.json"}:
            continue

        tf.extract(member, incoming_dir)
        fn = pathlib.Path(member.name)
        if fn.suffix == ".changes":
            if changes is not None:
                logger.error("Multiple .changes files in apt tarball")
                return
            changes = fn

    for sub in [".jsonindexes", "db", "dists"]:
        sync_to_local(
            bucket,
            pathlib.Path("/apt") / sub,
            local_apt_dir / sub,
            exact_timestamps=True,
        )

    sync_to_local(
        bucket,
        pathlib.Path("/apt") / "pool",
        local_apt_dir / "pool",
    )

    subprocess_run(
        [
            "reprepro",
            "-V",
            "-V",
            f"--confdir={str(reprepro_conf)}",
            f"--basedir={str(local_apt_dir)}",
            f"--logdir={str(reprepro_logs)}",
            "processincoming",
            "default",
            str(changes),
        ],
        cwd=incoming_dir,
        check=True,
    )

    result = subprocess_run(
        [
            "reprepro",
            f"--confdir={str(reprepro_conf)}",
            f"--basedir={str(local_apt_dir)}",
            f"--logdir={str(reprepro_logs)}",
            "dumpreferences",
        ],
        text=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=None,
    )

    repo_dists = set()
    for line in result.stdout.split("\n"):
        if not line.strip():
            continue

        dist, _, _ = line.partition("|")
        repo_dists.add(dist)

    list_format = (
        r"\0".join(
            (
                r"${$architecture}",
                r"${$component}",
                r"${package}",
                r"${version}",
                r"${$fullfilename}",
                r"${Installed-Size}",
                r"${Metapkg-Metadata}",
            )
        )
        + r"\n"
    )

    existing: dict[str, dict[tuple[str, str, str], Package]] = {}
    packages: dict[str, dict[tuple[str, str, str], Package]] = {}

    for dist in repo_dists:
        result = subprocess_run(
            [
                "reprepro",
                f"--confdir={str(reprepro_conf)}",
                f"--basedir={str(local_apt_dir)}",
                f"--logdir={str(reprepro_logs)}",
                f"--list-format={list_format}",
                "list",
                dist,
            ],
            text=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=None,
        )

        for line in result.stdout.split("\n"):
            if not line.strip():
                continue

            (
                arch,
                component,
                pkgname,
                pkgver,
                pkgfile,
                size,
                pkgmetadata_json,
            ) = line.split("\0")

            if component != "main" and not dist.endswith(component):
                index_dist = f"{dist}.{component}"
            else:
                index_dist = dist

            prev_dist_packages = existing.get(index_dist)
            if prev_dist_packages is None:
                idxfile = index_dir / f"{index_dist}.json"
                existing[index_dist] = prev_dist_packages = load_index(idxfile)

            dist_packages = packages.get(index_dist)
            if dist_packages is None:
                packages[index_dist] = dist_packages = {}

            if arch == "amd64":
                arch = "x86_64"

            is_metapackage = int(size) < 20

            relver, _, revver = pkgver.rpartition("-")

            m = slot_regexp.match(pkgname)
            if not m:
                logger.error("cannot parse package name: %s", pkgname)
                basename = pkgname
                slot = None
            else:
                basename = m.group(1)
                slot = m.group(2)

            if pkgmetadata_json:
                pkgmetadata = json.loads(pkgmetadata_json)
                if is_metapackage:
                    pkgmetadata["name"] = basename
                parsed_ver = pkgmetadata["version_details"]
            else:
                parsed_ver = parse_version(relver)
                pkgmetadata = {
                    "name": basename,
                    "version": relver,
                    "version_slot": slot,
                    "version_details": parsed_ver,
                    "architecture": arch,
                    "revision": revver,
                }

            version_key = format_version_key(parsed_ver, revver)
            ver_metadata = pkgmetadata["version_details"]["metadata"]
            index_key = (pkgmetadata["name"], version_key, arch)

            if index_key in prev_dist_packages:
                dist_packages[index_key] = prev_dist_packages[index_key]
                dist_packages[index_key]["architecture"] = arch
            else:
                if basename == "edgedb-server" and not ver_metadata.get(
                    "catalog_version"
                ):
                    if not pathlib.Path(pkgfile).exists():
                        logger.error(f"package file does not exist: {pkgfile}")
                    else:
                        catver = extract_catver_from_deb(pkgfile)
                        if catver is None:
                            logger.error(
                                f"cannot extract catalog version from {pkgfile}"
                            )
                        else:
                            ver_metadata["catalog_version"] = str(catver)
                            logger.info(
                                f"extracted catver {catver} from {pkgfile}"
                            )

                installref = InstallRef(
                    ref="{}={}-{}".format(pkgname, relver, revver),
                    type=None,
                    encoding=None,
                    verification={},
                )

                append_artifact(dist_packages, pkgmetadata, installref)

    for index_dist, dist_packages in packages.items():
        idxfile = index_dir / f"{index_dist}.json"
        with open(idxfile, "w") as f:
            json.dump({"packages": list(dist_packages.values())}, f)

    for sub in [".jsonindexes", "db", "dists"]:
        sync_to_s3(
            bucket,
            local_apt_dir / sub,
            pathlib.Path("/apt") / sub,
            cache_control="no-store, no-cache, private, max-age=0",
        )

    sync_to_s3(
        bucket,
        local_apt_dir / "pool",
        pathlib.Path("/apt") / "pool",
        cache_control="public, no-transform, max-age=315360000",
    )


def extract_catver_from_deb(path: str) -> int | None:
    cv_prefix = "EDGEDB_CATALOG_VERSION = "
    defines_pattern = (
        "*/usr/lib/*-linux-gnu/edgedb-server-*/lib/python*/site-packages/edb"
        + "/server/defines.py"
    )

    with tempfile.TemporaryDirectory() as _td:
        td = pathlib.Path(_td)
        subprocess_run(["ar", "x", path, "data.tar.xz"], cwd=_td)
        with tarfile.open(td / "data.tar.xz", "r:xz") as tarf:
            for member in tarf.getmembers():
                if fnmatch.fnmatch(member.path, defines_pattern):
                    df = tarf.extractfile(member)
                    if df is not None:
                        for lb in df.readlines():
                            line = lb.decode()
                            if line.startswith(cv_prefix):
                                return int(line[len(cv_prefix) :])

    return None


def process_rpm(
    cfg: Config,
    s3session: s3.S3ServiceResource,
    tf: tarfile.TarFile,
    metadata: dict[str, Any],
    bucket_name: str,
    temp_dir: pathlib.Path,
    local_dir: pathlib.Path,
) -> None:
    bucket = s3session.Bucket(bucket_name)
    incoming_dir = temp_dir / "incoming"
    incoming_dir.mkdir()
    local_rpm_dir = local_dir / "rpm"
    local_rpm_dir.mkdir(parents=True, exist_ok=True)
    index_dir = local_rpm_dir / ".jsonindexes"
    index_dir.mkdir(exist_ok=True)

    rpms = []
    for member in tf.getmembers():
        if member.name in {".", "build-metadata.json"}:
            continue
        tf.extract(member, incoming_dir)
        fn = pathlib.Path(member.name)
        if fn.suffix == ".rpm":
            rpms.append(fn)

    dist = metadata["dist"]
    channel = metadata["channel"]

    idx = dist
    if channel != "stable":
        idx += f".{channel}"

    dist_dir = pathlib.Path(dist) / channel / metadata["architecture"]
    local_dist_dir = local_rpm_dir / dist_dir
    local_dist_dir.mkdir(parents=True, exist_ok=True)

    sync_to_local(
        bucket,
        pathlib.Path("/rpm") / dist_dir,
        local_dist_dir,
        exact_timestamps=True,
    )

    sync_to_local(
        bucket,
        pathlib.Path("/rpm") / ".jsonindexes",
        index_dir,
        exact_timestamps=True,
    )

    repomd = local_dist_dir / "repodata" / "repomd.xml"
    if not repomd.exists():
        subprocess_run(
            [
                "createrepo_c",
                "--database",
                local_dist_dir,
            ],
            cwd=incoming_dir,
            check=True,
        )

    for rpm in rpms:
        logger.info(f"process_rpm: running `rpm --resign {rpm}`")
        subprocess_run(
            [
                "rpm",
                "--resign",
                rpm,
            ],
            input=b"\n",
            cwd=incoming_dir,
            check=True,
        )

        shutil.copy(incoming_dir / rpm, local_dist_dir / rpm)

    logger.info("process_rpm: running `createrepo_c --update`")
    subprocess_run(
        [
            "createrepo_c",
            "--update",
            local_dist_dir,
        ],
        check=True,
    )

    logger.info("process_rpm: signing repomd.xml")
    gpg_detach_sign(repomd)

    logger.info("process_rpm: loading index")
    idxfile = index_dir / f"{idx}.json"
    packages = load_index(idxfile)

    logger.info("process_rpm: fetching changelogs")
    changelogs = subprocess_run(
        [
            "dnf",
            f"--repofrompath={dist},{local_dist_dir}",
            f"--repoid={dist}",
            f"--releasever={dist}",
            "repoquery",
            "--changelogs",
            "-q",
            "*",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    lines_seen = 0
    lines: List[str] = []
    package: Optional[str] = None
    metadatas = {}

    for line in changelogs.stdout.splitlines():
        m = re.match(r"^Changelog for (?P<nevra>.*)$", line)
        if m:
            lines_seen = 0
            if lines and package:
                possibly_metadata_json = "\n".join(lines)
                try:
                    pkgmetadata = json.loads(possibly_metadata_json)
                except ValueError:
                    pkgmetadata = None
                else:
                    metadatas[package] = pkgmetadata
                lines.clear()
            package = m.group("nevra")
            assert package
        elif lines_seen >= 2 and package:
            if lines_seen == 2:
                lines.append(line.lstrip(" -"))
            else:
                lines.append(line)
        lines_seen += 1

    slot_index: dict[str, list[tuple[str, str, str, str]]] = {}

    result = subprocess_run(
        [
            "dnf",
            f"--repofrompath={dist},{local_dist_dir}",
            f"--repoid={dist}",
            f"--releasever={dist}",
            "repoquery",
            "--qf=%{name}|%{version}|%{release}|%{arch}|%{installsize}",
            "-q",
            "*",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    logger.info("process_rpm: updating index")
    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        pkgname, pkgver, release, arch, size = line.split("|")
        nevra = f"{pkgname}-{pkgver}-{release}.{arch}"
        pkgmetadata = metadatas.get(nevra)

        is_metapackage = int(size) == 0

        m = slot_regexp.match(pkgname)
        if not m:
            logger.info("cannot parse package name: {}".format(pkgname))
            basename = pkgname
            slot = None
        else:
            basename = m.group(1)
            slot = m.group(2)

        if not pkgmetadata:
            parsed_ver = parse_version(pkgver.replace("_", "-"))
            pkgmetadata = {
                "name": basename,
                "version": pkgver.replace("_", "-"),
                "version_slot": slot,
                "version_details": parsed_ver,
                "revision": release,
                "architecture": arch,
            }
        elif is_metapackage:
            pkgmetadata["name"] = basename

        version_key = format_version_key(
            pkgmetadata["version_details"], pkgmetadata["revision"]
        )

        slot_name = pkgmetadata["name"]
        if pkgmetadata.get("version_slot"):
            slot_name += f".{pkgmetadata['version_slot']}"
        slot_name += f".{pkgmetadata['architecture']}"
        slot_index.setdefault(slot_name, []).append(
            (
                version_key,
                pkgmetadata["name"],
                nevra,
                pkgmetadata["architecture"],
            )
        )

        installref = InstallRef(
            ref=nevra,
            type=None,
            encoding=None,
            verification={},
        )

        append_artifact(packages, pkgmetadata, installref)

    need_db_update = False
    if channel == "nightly":
        logger.info("process_rpm: collecting garbage")
        comp = functools.cmp_to_key(debian_support.version_compare)
        for slot_name, versions in slot_index.items():
            sorted_versions = list(
                sorted(
                    versions,
                    key=lambda v: comp(v[0]),
                    reverse=True,
                )
            )

            for ver_key, name, ver_nevra, arch in sorted_versions[3:]:
                logger.info(f"process_rpm: deleting outdated {ver_nevra}")
                packages.pop((name, ver_key, arch), None)
                outdated = local_dist_dir / f"{ver_nevra}.rpm"
                if outdated.exists():
                    os.unlink(outdated)
                need_db_update = True

    if need_db_update:
        logger.info("process_rpm: running `createrepo_c --update` (again)")
        subprocess_run(
            [
                "createrepo_c",
                "--update",
                local_dist_dir,
            ],
            check=True,
        )

    with open(idxfile, "w") as f:
        json.dump({"packages": list(packages.values())}, f)

    sync_to_s3(
        bucket,
        local_dist_dir / "repodata",
        pathlib.Path("/rpm") / dist_dir / "repodata",
        cache_control="no-store, no-cache, private, max-age=0",
    )

    sync_to_s3(
        bucket,
        index_dir,
        pathlib.Path("/rpm") / ".jsonindexes",
        cache_control="no-store, no-cache, private, max-age=0",
    )

    sync_to_s3(
        bucket,
        local_dist_dir,
        pathlib.Path("/rpm") / dist_dir,
        exclude="*",
        include="*.rpm",
        cache_control="public, no-transform, max-age=315360000",
    )


if __name__ == "__main__":
    main()
