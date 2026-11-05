#!/usr/bin/env python3
"""Fail-closed tests for the public YNWA and Team Status mirrors."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

from common import MirrorError, redact  # noqa: E402
from jsx_subset import iter_strings, parse_module, validate_tree  # noqa: E402
from prepare import prepare  # noqa: E402
from release import release  # noqa: E402
from sensitive import scan_text  # noqa: E402

YNWA_FIXTURE = HERE / "fixtures" / "ynwa-public"
TEAM_FIXTURE = HERE / "fixtures" / "team-status"
EXTERNAL = [
    "https://team.twocommanews.com",
    "https://twocommanews.com",
    "https://read.twocommanews.com",
    "https://trade.twocommanews.com",
    "https://lfc.twocommanews.com",
    "https://proprulewatch.com",
    "https://journalcompare.com",
]
ORIGINAL_INDEX_SHA = "9c8f8b9690b077b25356db9569eff228c8bdd8225f31eb8834af9247104bdc3e"
GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "public-mirrors-test",
    "GIT_AUTHOR_EMAIL": "public-mirrors-test@example.com",
    "GIT_COMMITTER_NAME": "public-mirrors-test",
    "GIT_COMMITTER_EMAIL": "public-mirrors-test@example.com",
}


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
        env=GIT_ENV,
    )
    return result.stdout


class PrepareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mirror-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_ynwa_rebase_preserves_external_links_and_bytes(self) -> None:
        out = self.tmp / "ynwa"
        notes = prepare("ynwa", str(YNWA_FIXTURE), str(out))
        self.assertTrue(any("prepared ynwa" in note for note in notes))
        page = (out / "index.html").read_text(encoding="utf-8")
        for url in EXTERNAL:
            self.assertIn(f'href="{url}"', page)
        self.assertIn('href="/ynwa/favicon.svg"', page)
        self.assertIn('src="/ynwa/avatars/gojo.png"', page)
        self.assertIn('src="icons/team.svg"', page)
        self.assertNotIn('href="/favicon.svg"', page)
        self.assertNotIn('href="/news/"', page)
        self.assertNotIn('href="/lfc/"', page)
        self.assertIn('href="#c"', (out / "icons" / "tcr.svg").read_text(encoding="utf-8"))
        for line in (HERE / "fixtures" / "ynwa-asset-sha256.txt").read_text().splitlines():
            digest, rel = line.split("  ", 1)
            payload = (out / rel).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), digest, rel)
            self.assertEqual((YNWA_FIXTURE / rel).read_bytes(), payload)
        self.assertTrue((out / ".nojekyll").is_file())
        self.assertEqual((out / ".nojekyll").read_bytes(), b"")
        referenced = [
            "favicon.svg",
            "icons/team.svg",
            "icons/tcn.svg",
            "icons/tcr.svg",
            "icons/tct.svg",
            "icons/lfc.png",
            "icons/prw.svg",
            "icons/jc.svg",
            "avatars/gojo.png",
            "avatars/boa.png",
            "avatars/tobi.png",
            "avatars/l.png",
            "avatars/ace.png",
            "avatars/levi.png",
            "avatars/klopp.png",
            "avatars/morgans.png",
            "avatars/zen.png",
            "avatars/dr-eggbot.png",
        ]
        for rel in referenced:
            self.assertTrue((out / rel).is_file(), rel)
        self.assertEqual(
            hashlib.sha256((YNWA_FIXTURE / "index.html").read_bytes()).hexdigest(),
            ORIGINAL_INDEX_SHA,
        )

    def test_published_trees_match_prepare(self) -> None:
        ynwa_out = self.tmp / "ynwa"
        team_out = self.tmp / "team"
        prepare("ynwa", str(YNWA_FIXTURE), str(ynwa_out))
        prepare("team", str(TEAM_FIXTURE), str(team_out))
        self.assertEqual(_files(ynwa_out), _files(REPO / "ynwa"))
        self.assertEqual(_files(team_out), _files(REPO / "team"))

    def test_team_page_keeps_source_text_and_timestamp(self) -> None:
        out = self.tmp / "team"
        prepare("team", str(TEAM_FIXTURE), str(out))
        page = (out / "index.html").read_text(encoding="utf-8")
        names, tree = parse_module((TEAM_FIXTURE / "TeamStatus.tsx").read_text(encoding="utf-8"))
        validate_tree(names, tree)
        for literal in iter_strings(tree):
            self.assertIn(literal, page)
        self.assertIn("As of Thu Nov 5, 2026, 7:00 AM PT.", page)
        self.assertIn("the UPS shipment was expected Wed Nov 4.", page)
        self.assertIn("termination for the policy on Nov 2", page)
        self.assertIn("NY Life (still says awaiting approval though it's done)", page)
        self.assertIn("Sixteen open board rows are more than 2 days old.", page)
        self.assertIn("HPMOR ch01 v9, RR ch01 v2", page)
        self.assertIn("Delivered the high-quality Team TwoComma logo", page)
        self.assertNotIn("refreshed", page.lower())
        self.assertNotIn("cursor.com/canvas/", page)
        self.assertNotIn("grok/canvas", page)
        self.assertNotIn("<script", page.lower())
        self.assertIn('lang="en"', page)
        self.assertIn("<table", page)
        self.assertIn('scope="col"', page)
        self.assertIn('scope="row"', page)
        for canvas_id in (
            "7160075c-3e2e-45e1-9e05-4a2b2a08f087",
            "b7dd82c4-7324-4829-9d67-68ba4fcb7147",
        ):
            self.assertNotIn(canvas_id, page)

    def test_unknown_targets_fail(self) -> None:
        for target in ("tcr", "tct", "team-twocomma", "news", "lfc", "canvas"):
            with self.assertRaises(MirrorError):
                prepare(target, str(YNWA_FIXTURE), str(self.tmp / target))

    def test_url_artifact_is_refused(self) -> None:
        with self.assertRaises(MirrorError):
            prepare("ynwa", "https://ynwa.twocommanews.com/", str(self.tmp / "out"))

    def test_ynwa_rejects_private_and_unsafe_paths(self) -> None:
        cases = {
            "tcr-dir": {"index.html": b"<html></html>", "tcr/page.html": b"private"},
            "team-dir": {"index.html": b"<html></html>", "team/index.html": b"canvas"},
            "worker": {"index.html": b"<html></html>", "_worker.js": b"export default {}"},
            "env": {"index.html": b"<html></html>", ".env": b"CLOUDFLARE_API_TOKEN=abc"},
            "zip-slip": {"../secrets.txt": b"nope", "index.html": b"<html></html>"},
            "secret-name": {"index.html": b"<html></html>", "passwords.html": b"x"},
        }
        for name, files in cases.items():
            archive = self.tmp / f"{name}.zip"
            _zip(archive, files)
            with self.assertRaises(MirrorError, msg=name):
                prepare("ynwa", str(archive), str(self.tmp / name))
            self.assertFalse((self.tmp / name / "index.html").exists(), name)

    def test_ynwa_strips_headers_and_rejects_missing_assets(self) -> None:
        archive = self.tmp / "headers.zip"
        _zip(
            archive,
            {
                "index.html": b"<!doctype html><title>YNWA</title>",
                "_headers": b"/*\n  Cache-Control: public\n",
                ".DS_Store": b"junk",
            },
        )
        out = self.tmp / "headers-out"
        notes = prepare("ynwa", str(archive), str(out))
        self.assertFalse((out / "_headers").exists())
        self.assertTrue(any("_headers" in note for note in notes))
        broken = self.tmp / "broken.zip"
        _zip(broken, {"index.html": b'<img src="icons/missing.svg">'})
        with self.assertRaises(MirrorError):
            prepare("ynwa", str(broken), str(self.tmp / "broken-out"))

    def test_team_fail_closed_cases(self) -> None:
        readme = (TEAM_FIXTURE / "README.md").read_text(encoding="utf-8")
        source = (TEAM_FIXTURE / "TeamStatus.tsx").read_text(encoding="utf-8")
        cases = {
            "policy": source.replace(
                "the policy",
                "policy number NYL-123456",
                1,
            ),
            "ups": source.replace(
                "the UPS shipment",
                "1Z999AA10123456784",
                1,
            ),
            "email": source.replace("Tobi", "tobi@example.com", 1),
            "long-id": source + "\naccount number 123456789\n",
            "token": source.replace("Zen", "ghp_abcdefghijklmnopqrstuvwxyz012345", 1),
            "grid": source.replace("<Text>", "<Grid>", 1).replace("</Text>", "</Grid>", 1),
            "comment": source.replace(
                "<Text>",
                "{/* do not drop this fact */}\n        <Text>",
                1,
            ),
            "unknown-prop": source.replace(
                "<Page ",
                '<Page sources={"this would have been dropped"} ',
                1,
            ),
            "wrong-title": source.replace('title="Team Status"', 'title="Team TwoComma"', 1),
        }
        for name, mutated in cases.items():
            bundle = self.tmp / name
            bundle.mkdir()
            (bundle / "TeamStatus.tsx").write_text(mutated, encoding="utf-8")
            (bundle / "README.md").write_text(readme, encoding="utf-8")
            with self.assertRaises(MirrorError, msg=name):
                prepare("team", str(bundle), str(self.tmp / f"{name}-out"))
            self.assertFalse((self.tmp / f"{name}-out" / "index.html").exists(), name)

    def test_team_rejects_other_canvas_and_extra_files(self) -> None:
        readme = (TEAM_FIXTURE / "README.md").read_text(encoding="utf-8")
        source = (TEAM_FIXTURE / "TeamStatus.tsx").read_text(encoding="utf-8")
        wrong = self.tmp / "wrong-canvas"
        wrong.mkdir()
        (wrong / "TeamStatus.tsx").write_text(source, encoding="utf-8")
        (wrong / "README.md").write_text(
            readme.replace(
                "7160075c-3e2e-45e1-9e05-4a2b2a08f087",
                "b7dd82c4-7324-4829-9d67-68ba4fcb7147",
            ),
            encoding="utf-8",
        )
        with self.assertRaises(MirrorError):
            prepare("team", str(wrong), str(self.tmp / "wrong-out"))
        extra = self.tmp / "extra"
        shutil.copytree(TEAM_FIXTURE, extra)
        (extra / "notes.txt").write_text("ignore me", encoding="utf-8")
        with self.assertRaises(MirrorError):
            prepare("team", str(extra), str(self.tmp / "extra-out"))

    def test_extra_table_cell_is_rendered(self) -> None:
        bundle = self.tmp / "extra-cell"
        bundle.mkdir()
        (bundle / "README.md").write_text(
            (TEAM_FIXTURE / "README.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (bundle / "TeamStatus.tsx").write_text(
            textwrap.dedent(
                """\
                import { Page, Section, Table, Text } from "grok/canvas";
                export default function App() {
                  return (
                    <Page title="Team Status" summary="As of Thu Nov 5, 2026, 7:00 AM PT.">
                      <Section heading="Each bot" caption="Kept caption">
                        <Table columns={["Bot", "Working on"]} rows={[["Zen", "News", "EXTRA CELL"]]} />
                        <Text>Kept paragraph.</Text>
                      </Section>
                    </Page>
                  );
                }
                """
            ),
            encoding="utf-8",
        )
        out = self.tmp / "extra-out"
        prepare("team", str(bundle), str(out))
        page = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("EXTRA CELL", page)
        self.assertIn("Kept caption", page)
        self.assertIn("Kept paragraph.", page)
        self.assertEqual(page.count("<th "), 4)

    def test_sensitive_scanner_accepts_the_sanitized_fixture(self) -> None:
        scan_text(
            (TEAM_FIXTURE / "TeamStatus.tsx").read_text(encoding="utf-8"),
            "TeamStatus.tsx",
        )
        scan_text(
            (TEAM_FIXTURE / "README.md").read_text(encoding="utf-8"),
            "README.md",
            allow_canvas_provenance=True,
        )

    def test_redact_hides_embedded_credentials(self) -> None:
        raw = "push failed https://x-access-token:ghp_abcdefghijklmnopqrstuvwxyz@github.com/org/repo"
        cleaned = redact(raw)
        self.assertNotIn("ghp_", cleaned)
        self.assertNotIn("x-access-token", cleaned)
        self.assertIn("[redacted]", cleaned)


class ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mirror-release-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bare = self.tmp / "bare.git"
        self.clone = self.tmp / "clone"
        subprocess.check_call(["git", "init", "--bare", "-b", "main", str(self.bare)], env=GIT_ENV)
        subprocess.check_call(["git", "clone", str(self.bare), str(self.clone)], env=GIT_ENV)
        (self.clone / "README.md").write_text("hub\n", encoding="utf-8")
        (self.clone / "news").mkdir()
        (self.clone / "news" / "keep.txt").write_text("news\n", encoding="utf-8")
        (self.clone / "lfc").mkdir()
        (self.clone / "lfc" / "keep.txt").write_text("lfc\n", encoding="utf-8")
        git("add", "--all", cwd=self.clone)
        git("commit", "-m", "base", cwd=self.clone)
        git("push", "origin", "HEAD:main", cwd=self.clone)

    def test_release_is_scoped_idempotent_and_retries(self) -> None:
        stage = self.tmp / "stage"
        prepare("team", str(TEAM_FIXTURE), str(stage))
        (self.clone / "DIRTY.txt").write_text("leave me\n", encoding="utf-8")
        other = self.tmp / "other"
        subprocess.check_call(["git", "clone", str(self.bare), str(other)], env=GIT_ENV)

        def before_push() -> None:
            (other / "news" / "keep.txt").write_text("news-updated\n", encoding="utf-8")
            git("add", "--all", cwd=other)
            git("commit", "-m", "TCN mirror: concurrent", cwd=other)
            git("push", "origin", "HEAD:main", cwd=other)

        message = release(
            "team",
            str(stage),
            str(self.clone),
            remote="origin",
            branch="main",
            before_push=before_push,
        )
        self.assertIn("pushed team", message)
        self.assertEqual((self.clone / "DIRTY.txt").read_text(encoding="utf-8"), "leave me\n")
        self.assertEqual(
            git("show", "origin/main:news/keep.txt", cwd=self.clone),
            "news-updated\n",
        )
        self.assertEqual(git("show", "origin/main:lfc/keep.txt", cwd=self.clone), "lfc\n")
        self.assertIn("Team Status", git("show", "origin/main:team/index.html", cwd=self.clone))
        published = git("ls-tree", "-r", "--name-only", "origin/main", cwd=self.clone).splitlines()
        team_files = [line for line in published if line.startswith("team/")]
        self.assertIn("team/index.html", team_files)
        self.assertIn("team/.nojekyll", team_files)
        tip_names = [
            line
            for line in git(
                "diff", "--name-only", "origin/main~1", "origin/main", cwd=self.clone
            ).splitlines()
            if line
        ]
        self.assertTrue(tip_names)
        self.assertTrue(all(line.startswith("team/") for line in tip_names))
        again = release("team", str(stage), str(self.clone), remote="origin", branch="main")
        self.assertIn("no changes", again)
        self.assertEqual(
            git("rev-list", "--count", "origin/main", cwd=self.clone).strip(),
            "3",
        )

    def test_rebase_conflict_does_not_force_push(self) -> None:
        stage = self.tmp / "stage"
        prepare("ynwa", str(YNWA_FIXTURE), str(stage))
        other = self.tmp / "other"
        subprocess.check_call(["git", "clone", str(self.bare), str(other)], env=GIT_ENV)

        def before_push() -> None:
            ynwa = other / "ynwa"
            ynwa.mkdir()
            (ynwa / "index.html").write_text("COMPETITOR\n", encoding="utf-8")
            git("add", "--all", cwd=other)
            git("commit", "-m", "other ynwa", cwd=other)
            git("push", "origin", "HEAD:main", cwd=other)

        with self.assertRaises(MirrorError) as caught:
            release(
                "ynwa",
                str(stage),
                str(self.clone),
                remote="origin",
                branch="main",
                before_push=before_push,
            )
        self.assertIn("conflicted", str(caught.exception))
        self.assertEqual(
            git("show", "origin/main:ynwa/index.html", cwd=self.clone),
            "COMPETITOR\n",
        )
        self.assertNotIn("--force", str(caught.exception))

    def test_lock_timeout_publishes_nothing(self) -> None:
        import fcntl

        common = Path(git("rev-parse", "--git-common-dir", cwd=self.clone).strip())
        if not common.is_absolute():
            common = (self.clone / common).resolve()
        handle = open(common / "public-mirrors.lock", "a", encoding="utf-8")
        self.addCleanup(handle.close)
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stage = self.tmp / "stage"
        prepare("team", str(TEAM_FIXTURE), str(stage))
        with self.assertRaises(MirrorError) as caught:
            release(
                "team",
                str(stage),
                str(self.clone),
                remote="origin",
                branch="main",
                lock_timeout=0,
            )
        self.assertIn("lock", str(caught.exception))
        self.assertNotIn("team/index.html", git("ls-tree", "-r", "--name-only", "origin/main", cwd=self.clone))


class HookTests(unittest.TestCase):
    def test_hook_and_sync_usage(self) -> None:
        hook = subprocess.run(
            [str(HERE / "integration-hook.sh")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(hook.returncode, 2)
        self.assertIn("not installed", hook.stderr)
        sync = subprocess.run(
            [str(HERE / "sync.sh"), "tcr", str(YNWA_FIXTURE)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(sync.returncode, 1)
        self.assertIn("unknown target", sync.stderr)
        url = subprocess.run(
            [str(HERE / "sync.sh"), "ynwa", "https://example.com/site.zip"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(url.returncode, 1)
        env = os.environ.copy()
        env.pop("PUBLIC_MIRROR_REPO", None)
        unconfigured = subprocess.run(
            [str(HERE / "sync.sh"), "team", str(TEAM_FIXTURE)],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(unconfigured.returncode, 3)
        self.assertIn("nothing was published", unconfigured.stderr)
        self.assertIn("prepared team", unconfigured.stdout + unconfigured.stderr)

    def test_sources_do_not_reset_force_or_poll(self) -> None:
        blobs = []
        for path in HERE.iterdir():
            if path.name == "test_public_mirrors.py":
                continue
            if path.suffix in {".py", ".sh"}:
                blobs.append(path.read_text(encoding="utf-8"))
        text = "\n".join(blobs)
        for banned in (
            "reset --hard",
            "push --force",
            "push -f",
            "+HEAD",
            "pages/builds",
            "sleep 30",
            "GH_TOKEN",
            "GITHUB_TOKEN",
            "CLOUDFLARE_API_TOKEN",
        ):
            self.assertNotIn(banned, text)

    def test_protected_repository_paths_are_untouched(self) -> None:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                "main",
                "--",
                "news",
                "lfc",
                "index.html",
                "README.md",
                "favicon.svg",
                "icons",
            ],
            cwd=REPO,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout.strip(), "")


def _files(root: Path) -> dict[str, bytes]:
    found = {}
    for path in root.rglob("*"):
        if path.is_file():
            found[path.relative_to(root).as_posix()] = path.read_bytes()
    return found


def _zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
