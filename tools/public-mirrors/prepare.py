#!/usr/bin/env python3
"""Prepare one public mirror. This does not publish and does not contact the network.

Source preparation and public release are separate. prepare.py only writes a
staging directory. release.py is what updates the GitHub Pages checkout.
"""

from __future__ import annotations

import argparse
import sys

from common import MirrorError, assert_target
from team_prepare import prepare_team
from ynwa_prepare import prepare_ynwa


def prepare(target: str, artifact: str, out_dir: str) -> list[str]:
    if artifact.startswith(("http://", "https://", "file://")):
        raise MirrorError("refusing a URL artifact. Pass a local file or directory.")
    subdir = assert_target(target)
    if subdir == "ynwa":
        return prepare_ynwa(artifact, out_dir)
    if subdir == "team":
        return prepare_team(artifact, out_dir)
    raise MirrorError(f"unknown target page: {target}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a public YNWA or Team Status mirror staging directory.")
    parser.add_argument("--target", required=True, help="ynwa or team")
    parser.add_argument("--artifact", required=True, help="local directory or zip")
    parser.add_argument("--out", required=True, help="empty output directory")
    args = parser.parse_args(argv)
    try:
        for line in prepare(args.target, args.artifact, args.out):
            print(line)
    except MirrorError as exc:
        print(f"public-mirrors: ERROR {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
