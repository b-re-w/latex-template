#!/usr/bin/env python3
"""Pick a venue and lay out paper/. Run this once when starting a new paper.

    uv run init.py               list available venues
    uv run init.py WACV          initialise for WACV
    uv run init.py WACV --no-build

What it does:
    1. expand templates/<venue>/skeleton/ into paper/
    2. copy style files from templates/<venue>/official/ into paper/
       (rule: *.sty *.cls *.bst, plus anything listed in assets.txt)
    3. copy the formatting guidelines into docs/references/<venue>/
    4. run a verification build so a broken copy is caught now, not at submission

It deletes nothing; removing templates/ is left to the user.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
PAPER = ROOT / "paper"
ASSET_SUFFIXES = {".sty", ".cls", ".bst"}


def venues():
    """Venues split into (ready, pending) by whether a skeleton exists."""
    ready, pending = [], []
    if TEMPLATES.is_dir():
        for d in sorted(p for p in TEMPLATES.iterdir() if p.is_dir()):
            target = ready if (d / "skeleton" / "main.tex").exists() else pending
            target.append(d.name)
    return ready, pending


def resolve(name, ready):
    for v in ready:
        if v.lower() == name.lower():
            return v
    return None


def assets_for(tpl):
    """Files to copy into paper/ for this venue."""
    official = tpl / "official"
    files = [f for f in sorted(official.iterdir())
             if f.is_file() and f.suffix in ASSET_SUFFIXES]

    extra = tpl / "assets.txt"
    if extra.exists():
        for line in extra.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            path = official / line
            if not path.exists():
                sys.exit(f"assets.txt lists '{line}' but it is not in official/")
            files.append(path)
    return files


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("venue", nargs="?", help="venue name, e.g. WACV")
    ap.add_argument("--no-build", action="store_true", help="skip the verification build")
    opts = ap.parse_args()

    ready, pending = venues()

    if not opts.venue:
        print("usage: uv run init.py <venue>")
        print(f"available: {', '.join(ready) if ready else 'none'}")
        if pending:
            print(f"no skeleton yet: {', '.join(pending)}")
        return

    venue = resolve(opts.venue, ready)
    if venue is None:
        sys.exit(f"'{opts.venue}' is not available. "
                 f"Available: {', '.join(ready) if ready else 'none'}")

    tpl = TEMPLATES / venue

    # Refuse to overwrite a manuscript that is already being written.
    main_tex = PAPER / "main.tex"
    if main_tex.exists() and main_tex.stat().st_size > 0:
        sys.exit("paper/main.tex is not empty, so this looks already initialised.\n"
                 "To start over: git checkout -- paper && git clean -fd paper")

    copied = []

    for f in sorted((tpl / "skeleton").iterdir()):
        if f.is_file():
            shutil.copy2(f, PAPER / f.name)
            copied.append(f"paper/{f.name}")

    files = assets_for(tpl)
    if not files:
        sys.exit(f"no style files found in {tpl}/official/")
    for f in files:
        shutil.copy2(f, PAPER / f.name)
        copied.append(f"paper/{f.name}")

    # docs/ is never uploaded to the publisher, so guidelines are safe there.
    guides = [f for f in sorted((tpl / "official").iterdir())
              if f.is_file() and f.suffix == ".md"]
    if guides:
        docdir = ROOT / "docs" / "references" / venue
        docdir.mkdir(parents=True, exist_ok=True)
        for f in guides:
            shutil.copy2(f, docdir / f.name)
            copied.append(f"docs/references/{venue}/{f.name}")

    print(f"\n[{venue}] initialised. Copied:")
    for c in copied:
        print(f"  {c}")

    if not opts.no_build:
        print("\nVerification build...")
        code = subprocess.run([sys.executable, str(ROOT / "build.py")]).returncode
        if code != 0 or not (ROOT / "build" / "main.pdf").exists():
            print("warning: the build failed. Check build/main.log", file=sys.stderr)

    print("\nNext:")
    print("  1. fill in the title and authors in paper/main.tex")
    print("  2. build: uv run build.py")
    print("  3. templates/ can be deleted now")
    print("     (only the contents of paper/ go to Overleaf or the submission site)")


if __name__ == "__main__":
    main()
