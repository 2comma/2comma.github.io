"""Prepare a public YNWA deployment artifact for /ynwa/.

The input is a static site root (directory or zip), the same shape as the
public ynwa.twocommanews.com upload. Root-absolute same-site URLs are rebased
under /ynwa/. External project links are left unchanged. Files that are not
on the public allowlist abort the prepare; they are not omitted.
"""

from __future__ import annotations

import os
import re
import stat
import zipfile
from pathlib import Path

from sensitive import scan_bytes, scan_text

from common import MirrorError

MAX_FILES = 200
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024

ROOT_FILE = re.compile(
    r"^[a-z0-9][a-z0-9._-]{0,80}\.(html|css|js|svg|txt|ico|png|webmanifest)$"
)
TREE_FILES = {
    "avatars": re.compile(
        r"^avatars/[a-z0-9][a-z0-9._-]{0,80}\.(png|jpg|jpeg|webp|gif|svg)$"
    ),
    "icons": re.compile(
        r"^icons/[a-z0-9][a-z0-9._-]{0,80}\.(png|jpg|jpeg|webp|gif|svg|ico)$"
    ),
}
DENY_SEGMENTS = {
    ".git",
    "node_modules",
    "tcr",
    "tct",
    "team",
    "canvas",
    "private",
    "secrets",
    "credentials",
    "workers",
    "src",
    "dist",
    "jack",
    "__pycache__",
    "__macosx",
}
SECRET_NAME = re.compile(r"(?i)secret|credential|password|token|private")
STRIP_BASENAMES = {"_headers", "_redirects", ".ds_store", "thumbs.db"}
REJECT_BASENAMES = {
    "_worker.js",
    "_routes.json",
    "wrangler.toml",
    "wrangler.json",
    "wrangler.jsonc",
}
TEXT_SUFFIXES = (".html", ".css", ".js", ".svg", ".json", ".txt", ".webmanifest")
LOCAL_ATTR = re.compile(
    r"""(?:href|src|data-src|action|data-lp|poster)\s*=\s*(["'])(.*?)\1""",
    re.I,
)
SRCSET_ATTR = re.compile(r"""srcset\s*=\s*(["'])(.*?)\1""", re.I)
CSS_URL = re.compile(r"""url\(\s*(["']?)(.*?)\1\s*\)""", re.I)


def prepare_ynwa(artifact: str, out_dir: str) -> list[str]:
    files, omitted = load_site(artifact)
    check_limits(files)
    kept: dict[str, bytes] = {}
    for rel, data in files.items():
        if not allowed(rel):
            raise MirrorError(
                f"path is not on the YNWA public allowlist: {rel}. "
                "Nothing was published."
            )
        scan_payload(rel, data)
        kept[rel] = data
    if "index.html" not in kept:
        raise MirrorError("YNWA artifact has no index.html. Nothing was published.")
    rebased = rebase_tree(kept, "/ynwa")
    check_local_links(rebased, "/ynwa")
    rebased[".nojekyll"] = b""
    write_tree(out_dir, rebased)
    notes = [f"public-mirrors: prepared ynwa ({len(rebased)} files)"]
    if omitted:
        notes.append("omitted deploy metadata: " + ", ".join(omitted))
    return notes


def prepare_root_hub(artifact: str, out_dir: str) -> list[str]:
    """Stage the public hub for the repository root. Paths stay root-absolute."""
    from root_ownership import is_owned, is_protected

    files, omitted = load_site(artifact)
    check_limits(files)
    kept: dict[str, bytes] = {}
    for rel, data in files.items():
        if is_protected(rel):
            raise MirrorError(
                f"refusing protected path {rel}. news, lfc, team, tools, and ynwa are not YNWA root files."
            )
        if not is_owned(rel):
            raise MirrorError(
                f"path is not on the YNWA root ownership manifest: {rel}. Nothing was published."
            )
        scan_payload(rel, data)
        kept[rel] = data
    if "index.html" not in kept:
        raise MirrorError("YNWA artifact has no index.html. Nothing was published.")
    validate_canonical_references(kept)
    write_tree(out_dir, kept)
    notes = [f"public-mirrors: prepared root hub ({len(kept)} files)"]
    if omitted:
        notes.append("omitted deploy metadata: " + ", ".join(omitted))
    return notes


def load_site(artifact: str) -> tuple[dict[str, bytes], list[str]]:
    path = Path(artifact)
    if not path.exists():
        raise MirrorError(f"artifact does not exist: {artifact}")
    if path.is_symlink():
        raise MirrorError("artifact path is a symlink")
    if path.is_dir():
        raw = read_directory(path)
    elif path.is_file() and zipfile.is_zipfile(path):
        raw = read_zip(path)
    else:
        raise MirrorError("YNWA artifact must be a directory or a zip file")
    return unwrap_site(raw)


def read_directory(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
        dirnames[:] = sorted(dirnames)
        for name in dirnames:
            candidate = Path(dirpath) / name
            if candidate.is_symlink():
                raise MirrorError(f"symlink rejected: {candidate}")
        for name in sorted(filenames):
            candidate = Path(dirpath) / name
            if candidate.is_symlink():
                raise MirrorError(f"symlink rejected: {candidate}")
            rel = candidate.relative_to(path).as_posix()
            check_relative(rel)
            data = candidate.read_bytes()
            files[rel] = data
    if not files:
        raise MirrorError("artifact directory is empty")
    return files


def read_zip(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            if name.endswith("/"):
                check_relative(name.rstrip("/"))
                continue
            check_relative(name)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise MirrorError(f"symlink rejected in zip: {name}")
            if info.file_size > MAX_FILE_BYTES:
                raise MirrorError(f"file exceeds size limit: {name}")
            data = archive.read(info)
            if len(data) != info.file_size:
                raise MirrorError(f"zip size mismatch: {name}")
            files[name] = data
    if not files:
        raise MirrorError("artifact zip has no files")
    return files


def check_relative(name: str) -> None:
    if not name or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        raise MirrorError(f"unsafe absolute path: {name}")
    if name.startswith("__MACOSX/") or name.rstrip("/") == "__MACOSX":
        return
    parts = [part for part in name.split("/") if part != ""]
    if any(part == ".." for part in name.split("/")):
        raise MirrorError(f"unsafe path: {name}")
    for part in parts:
        if part in ("", ".", ".."):
            raise MirrorError(f"unsafe path: {name}")
        lowered = part.lower()
        if lowered in STRIP_BASENAMES:
            continue
        if lowered in DENY_SEGMENTS or part.startswith("."):
            raise MirrorError(f"unsafe or private path: {name}")
        if SECRET_NAME.search(part):
            raise MirrorError(f"unsafe or private path: {name}")
        if lowered in REJECT_BASENAMES:
            raise MirrorError(f"unsafe deploy file: {name}")


def unwrap_site(files: dict[str, bytes]) -> tuple[dict[str, bytes], list[str]]:
    omitted: list[str] = []
    content = []
    for name in files:
        base = name.split("/")[-1]
        if name.startswith("__MACOSX/") or base.lower() in {"thumbs.db"}:
            omitted.append(name)
            continue
        content.append(name)
    if not content:
        raise MirrorError("artifact has no content files")
    root_files = [name for name in content if "/" not in name]
    top_dirs = {name.split("/")[0] for name in content if "/" in name}
    prefix = ""
    if "index.html" in files and root_files:
        prefix = ""
    elif not root_files and len(top_dirs) == 1:
        only = next(iter(top_dirs))
        if f"{only}/index.html" not in files:
            raise MirrorError("wrapped artifact has no index.html")
        prefix = only + "/"
    else:
        raise MirrorError(
            "unrecognized YNWA artifact layout. "
            "Expected index.html at the root, or one wrapper directory that contains it."
        )
    site: dict[str, bytes] = {}
    for name, data in files.items():
        base = name.split("/")[-1]
        if name.startswith("__MACOSX/") or base.lower() in {"thumbs.db"}:
            continue
        if prefix and not name.startswith(prefix):
            if base.lower() in STRIP_BASENAMES:
                omitted.append(name)
                continue
            raise MirrorError(f"file outside the YNWA site root: {name}")
        rel = name[len(prefix):] if prefix else name
        if not rel:
            continue
        if base.lower() in STRIP_BASENAMES:
            scan_if_text(rel, data)
            omitted.append(rel)
            continue
        site[rel] = data
    return site, omitted


def check_limits(files: dict[str, bytes]) -> None:
    if len(files) > MAX_FILES:
        raise MirrorError("YNWA artifact has too many files")
    total = 0
    for rel, data in files.items():
        if len(data) > MAX_FILE_BYTES:
            raise MirrorError(f"file exceeds size limit: {rel}")
        total += len(data)
    if total > MAX_TOTAL_BYTES:
        raise MirrorError("YNWA artifact exceeds the total size limit")


def allowed(rel: str) -> bool:
    if "/" in rel:
        top = rel.split("/")[0]
        pattern = TREE_FILES.get(top)
        return bool(pattern and pattern.fullmatch(rel) and rel.count("/") == 1)
    return bool(ROOT_FILE.fullmatch(rel))


def scan_payload(rel: str, data: bytes) -> None:
    scan_bytes(data, rel)
    scan_if_text(rel, data)


def scan_if_text(rel: str, data: bytes) -> None:
    if rel.lower().endswith(TEXT_SUFFIXES):
        try:
            text = data.decode("utf-8")
        except UnicodeError as exc:
            raise MirrorError(f"text file is not utf-8: {rel}") from exc
        scan_text(text, rel)


def rebase_tree(files: dict[str, bytes], base: str) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for rel, data in files.items():
        if rel.lower().endswith(TEXT_SUFFIXES):
            text = data.decode("utf-8")
            rewritten = rebase_text(text, base)
            scan_text(rewritten, rel)
            out[rel] = rewritten.encode("utf-8")
        else:
            out[rel] = data
    return out


def rebase_text(text: str, base: str) -> str:
    """Prefix root-absolute URLs with base. External and fragment URLs stay."""
    root = "/" + base.strip("/")
    guard = re.escape(root.strip("/"))

    def attr_re(names: str) -> re.Pattern[str]:
        return re.compile(
            rf"""((?:{names})=\\?["'])/(?!/)(?!{guard}(?:/|["']))"""
        )

    text = attr_re("href|src|data-src|action|data-lp|poster").sub(
        lambda match: match.group(1) + root + "/",
        text,
    )
    text = attr_re("content").sub(
        lambda match: match.group(1) + root + "/",
        text,
    )

    def rebase_srcset(match: re.Match[str]) -> str:
        prefix, value = match.group(1), match.group(2)
        parts = []
        for chunk in value.split(","):
            piece = chunk.strip()
            if not piece:
                continue
            bits = piece.split()
            url = bits[0]
            rest = " ".join(bits[1:])
            if url.startswith("/") and not url.startswith("//") and not url.startswith(root + "/") and url != root:
                url = root + url
            parts.append(url + ((" " + rest) if rest else ""))
        return prefix + ", ".join(parts)

    text = re.sub(
        r"""(srcset=\\?["'])([^"']*)""",
        rebase_srcset,
        text,
        flags=re.I,
    )
    text = re.sub(
        rf"""url\((["']?)/(?!/)(?!{guard}/)""",
        lambda match: "url(" + match.group(1) + root + "/",
        text,
    )
    return text


def validate_canonical_references(files: dict[str, bytes]) -> None:
    """Check a Cloudflare dist whose root-absolute URLs are still site-root paths.

    This does not rewrite the dist. `/favicon.svg` must exist as `favicon.svg`.
    """
    for rel, data in files.items():
        if not rel.lower().endswith(TEXT_SUFFIXES):
            continue
        text = data.decode("utf-8")
        urls = [match.group(2) for match in LOCAL_ATTR.finditer(text)]
        urls.extend(match.group(2) for match in CSS_URL.finditer(text))
        for match in SRCSET_ATTR.finditer(text):
            for chunk in match.group(2).split(","):
                piece = chunk.strip()
                if piece:
                    urls.append(piece.split()[0])
        for url in urls:
            _require_canonical_target(files, rel, url)


def _require_canonical_target(files: dict[str, bytes], owner: str, url: str) -> None:
    stripped = url.strip()
    if not stripped or stripped.startswith("#"):
        return
    lowered = stripped.lower()
    if lowered.startswith("javascript:"):
        raise MirrorError(f"javascript URL in {owner}")
    if lowered.startswith(("mailto:", "tel:", "data:", "https:", "http:")) or stripped.startswith("//"):
        return
    if stripped.startswith("/"):
        rel_path = stripped[1:].split("#", 1)[0].split("?", 1)[0]
        if rel_path.endswith("/"):
            rel_path += "index.html"
        if rel_path not in files:
            raise MirrorError(f"missing local asset {stripped} referenced by {owner}")
        return
    path = _resolve_relative(owner, stripped)
    if path not in files:
        raise MirrorError(f"missing local asset {stripped} referenced by {owner}")


def check_local_links(files: dict[str, bytes], base: str) -> None:
    root = "/" + base.strip("/")
    for rel, data in files.items():
        if not rel.lower().endswith(TEXT_SUFFIXES):
            continue
        text = data.decode("utf-8")
        urls = [match.group(2) for match in LOCAL_ATTR.finditer(text)]
        urls.extend(match.group(2) for match in CSS_URL.finditer(text))
        for match in SRCSET_ATTR.finditer(text):
            for chunk in match.group(2).split(","):
                piece = chunk.strip()
                if piece:
                    urls.append(piece.split()[0])
        for url in urls:
            _require_local_target(files, rel, url, root)


def _require_local_target(files: dict[str, bytes], owner: str, url: str, root: str) -> None:
    stripped = url.strip()
    if not stripped or stripped.startswith("#"):
        return
    lowered = stripped.lower()
    if lowered.startswith(("mailto:", "tel:", "data:", "https:", "http:")) or stripped.startswith("//"):
        if lowered.startswith("javascript:"):
            raise MirrorError(f"javascript URL in {owner}")
        return
    if lowered.startswith("javascript:"):
        raise MirrorError(f"javascript URL in {owner}")
    if stripped.startswith("/"):
        if stripped == root or stripped.startswith(root + "/"):
            rel = stripped[len(root):].lstrip("/")
            if rel in ("",) or rel.endswith("/"):
                candidate = (rel.rstrip("/") + "/index.html").lstrip("/")
            else:
                candidate = rel.split("#", 1)[0].split("?", 1)[0]
            if candidate and candidate not in files and not candidate.endswith("/index.html"):
                html_candidate = candidate + "/index.html" if not candidate.endswith(".html") else None
                if candidate not in files and (html_candidate not in files if html_candidate else True):
                    # Directory links such as /ynwa/ are satisfied by index.html.
                    if candidate not in files:
                        raise MirrorError(
                            f"missing local asset {stripped} referenced by {owner}"
                        )
            elif candidate and candidate not in files:
                raise MirrorError(f"missing local asset {stripped} referenced by {owner}")
            return
        raise MirrorError(
            f"root-absolute URL was not rebased under {root}: {stripped} in {owner}"
        )
    path = _resolve_relative(owner, stripped)
    if path not in files:
        raise MirrorError(f"missing local asset {stripped} referenced by {owner}")


def _resolve_relative(owner: str, url: str) -> str:
    clean = url.split("#", 1)[0].split("?", 1)[0]
    base = owner.split("/")[:-1]
    for part in clean.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not base:
                raise MirrorError(f"relative URL escapes the site: {url} in {owner}")
            base.pop()
            continue
        base.append(part)
    return "/".join(base)


def write_tree(out_dir: str, files: dict[str, bytes]) -> None:
    out = Path(out_dir)
    if out.exists():
        if any(out.iterdir()):
            raise MirrorError(f"output directory is not empty: {out_dir}")
    else:
        out.mkdir(parents=True)
    root = out.resolve()
    for rel, data in sorted(files.items()):
        dest = out.joinpath(*rel.split("/"))
        if dest.is_symlink():
            raise MirrorError(f"refusing to write through a symlink: {rel}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        resolved = dest.resolve()
        if resolved != root and root not in resolved.parents:
            raise MirrorError(f"output path escapes the staging directory: {rel}")
        dest.write_bytes(data)
