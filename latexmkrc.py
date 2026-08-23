#!/usr/bin/env python3
"""Build the paper, or initialise it from a conference template.

    uv run latexmkrc.py                 incremental build
    uv run latexmkrc.py --watch         rebuild on save
    uv run latexmkrc.py --clean         remove everything the build produced
    uv run latexmkrc.py --init WACV     lay out paper/ for a venue
    uv run latexmkrc.py --init          list available venues

Initialising copies a venue folder from templates/ over paper/ and then deletes
templates/ entirely: a paper targets one venue, and the catalogue has no further
purpose once the choice is made.

The TeX toolchain lives in .venv/tinytex and is installed on first use, so
nothing is installed system-wide and deleting .venv removes every trace of it.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEXDIR = ROOT / ".venv" / "tinytex"
TEMPLATES = ROOT / "templates"
PAPER = ROOT / "paper"


# --------------------------------------------------------------------------
# toolchain
# --------------------------------------------------------------------------

def tex_bin_dir():
    """Return the bin directory of the TeX install, or None if not installed.

    TeX Live lays its binaries out under bin/<platform>/ (bin/windows,
    bin/universal-darwin, bin/x86_64-linux). Rather than branching on the
    platform, pick whichever subdirectory holds latexmk.
    """
    bin_root = TEXDIR / "bin"
    if not bin_root.is_dir():
        return None
    for cand in sorted(p for p in bin_root.iterdir() if p.is_dir()):
        if (cand / "latexmk.exe").exists() or (cand / "latexmk").exists():
            return cand
    return None


def tool(name, binpath):
    """Resolve a tool inside the toolchain.

    On Windows some of these are .bat wrappers (tlmgr.bat), which CreateProcess
    will not find from a bare name, so resolve to a full path first.
    """
    return shutil.which(name, path=str(binpath)) or name


def tex_env(binpath):
    env = os.environ.copy()
    env["PATH"] = str(binpath) + os.pathsep + env.get("PATH", "")
    return env


def install_tex():
    """Download TinyTeX into .venv and return its bin directory."""
    try:
        import pytinytex
    except ImportError:
        sys.exit("pytinytex is missing. Run 'uv sync' first.")

    print("Installing the TeX toolchain into .venv/tinytex (about 500 MB).", flush=True)
    print("It is confined to this repository; deleting .venv removes it.", flush=True)
    TEXDIR.parent.mkdir(parents=True, exist_ok=True)
    # download_folder defaults to the working directory, which would leave a
    # few hundred MB of archive in the repository root. Stage it under .venv
    # instead of the system temp directory, so nothing is written outside the
    # repository and deleting .venv is guaranteed to reclaim everything.
    with tempfile.TemporaryDirectory(dir=TEXDIR.parent) as tmp:
        pytinytex.download_tinytex(variation=2, target_folder=TEXDIR,
                                   download_folder=tmp)

    binpath = tex_bin_dir()
    if binpath is None:
        sys.exit("Install finished but latexmk was not found.")

    # tlmgr refuses to install packages until it has updated itself.
    print("Updating tlmgr...", flush=True)
    subprocess.run([tool("tlmgr", binpath), "update", "--self"],
                   env=tex_env(binpath),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return binpath


# --------------------------------------------------------------------------
# missing packages
# --------------------------------------------------------------------------

def file_visible(filename, binpath, env):
    """True once TeX can actually resolve the file."""
    result = subprocess.run([tool("kpsewhich", binpath), filename],
                            env=env, capture_output=True, text=True)
    return bool(result.stdout.strip())


def resolve_package(filename, binpath, env):
    """Find the CTAN package that ships a file.

    For a .sty or .cls the package is usually named after the file, so try that
    first and save a network round trip. Otherwise ask tlmgr, skipping hits
    under doc/ where the same name often appears as example material.
    """
    stem = filename.rsplit(".", 1)[0]
    if filename.endswith((".sty", ".cls")):
        return stem

    result = subprocess.run(
        [tool("tlmgr", binpath), "search", "--global", "--file", filename],
        env=env, capture_output=True, text=True)

    package = None
    for line in result.stdout.splitlines():
        if not line.startswith((" ", "\t")):
            package = line.rstrip(":").strip() or None
        elif package and "/doc/" not in line and line.strip().endswith("/" + filename):
            return package
    return stem


def install_files(filenames, binpath, env):
    """Install whatever ships the given files, and wait until TeX sees them.

    On Windows `tlmgr update --self` hands the infrastructure swap to a
    detached batch file and returns early, so a command issued right after it
    can race with the update. Rather than guessing a delay, poll until the
    file actually resolves.
    """
    for filename in filenames:
        package = resolve_package(filename, binpath, env)
        for _ in range(8):
            result = subprocess.run([tool("tlmgr", binpath), "install", package],
                                    env=env, capture_output=True, text=True)
            if "needs to be updated" in (result.stdout + result.stderr):
                subprocess.run([tool("tlmgr", binpath), "update", "--self"],
                               env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                time.sleep(2)
                continue

            # Refresh the filename database so new files become visible, and
            # the font map, which tlmgr can leave half-written when its own
            # infrastructure update is still in flight.
            for refresh in ("mktexlsr", "updmap"):
                subprocess.run([tool(refresh, binpath)], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if file_visible(filename, binpath, env):
                break
            time.sleep(2)
        else:
            print(f"warning: {filename} could not be installed", file=sys.stderr)


def missing_files(build_dir):
    """Files the last build reported as missing.

    pdflatex records missing packages in main.log, but a missing bibliography
    style only shows up in bibtex's own main.blg, so both have to be read.
    """
    names = []

    log = build_dir / "main.log"
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if "File `" in line and "' not found" in line:
                name = line.split("File `", 1)[1].split("'", 1)[0]
                if name.endswith((".sty", ".cls")):
                    names.append(name)

    blg = build_dir / "main.blg"
    if blg.exists():
        for line in blg.read_text(encoding="utf-8", errors="replace").splitlines():
            if "couldn't open style file" in line:
                names.append(line.split("style file", 1)[1].strip())

    return sorted(set(names))


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def run_latexmk(extra, env, binpath, force=False):
    """Run latexmk in paper/.

    latexmk remembers a failed run and refuses to repeat it, so a retry after
    installing the package that caused the failure needs -g to force it.
    """
    args = [tool("latexmk", binpath), "-r", str(ROOT / "latexmkrc")]
    if force:
        args.append("-g")
    args += extra + ["main.tex"]
    return subprocess.run(args, cwd=PAPER, env=env).returncode


def build(opts):
    binpath = tex_bin_dir() or install_tex()
    env = tex_env(binpath)

    # -C removes the PDF too, so --clean and the copied paper/main.pdf agree.
    extra = (["-C"] if opts.clean else []) + (["-pvc"] if opts.watch else [])
    code = run_latexmk(extra, env, binpath)

    if opts.clean:
        # latexmk only knows about build/; the copies are ours to remove.
        for name in ("main.pdf", "main.synctex.gz"):
            (PAPER / name).unlink(missing_ok=True)
        return code

    # TinyTeX ships a fixed package set and does not fetch what is missing.
    # pdflatex stops at the first missing file, so each round reveals at most
    # one more of them; keep installing and rebuilding until nothing is left.
    seen = set()
    while code != 0:
        missing = [f for f in missing_files(ROOT / "build") if f not in seen]
        if not missing:
            break
        seen.update(missing)
        print(f"Installing missing packages: {', '.join(missing)}", flush=True)
        install_files(missing, binpath, env)
        code = run_latexmk(extra, env, binpath, force=True)

    # latexmkrc copies the finished PDF here on success.
    pdf = PAPER / "main.pdf"
    if code == 0 and pdf.exists():
        print(f"PDF: {pdf}")
    return code


# --------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------

# Documents the template itself rather than being part of the paper.
SKIP = {"README.md"}


def venues():
    if not TEMPLATES.is_dir():
        return []
    return sorted(d.name for d in TEMPLATES.iterdir()
                  if d.is_dir() and (d / "main.tex").exists())


def init(name):
    available = venues()

    if not name:
        if not available:
            sys.exit("templates/ is gone, so this paper is already initialised.")
        print("usage: uv run latexmkrc.py --init <venue>")
        print(f"available: {', '.join(available)}")
        return 0

    venue = next((v for v in available if v.lower() == name.lower()), None)
    if venue is None:
        sys.exit(f"'{name}' is not available. "
                 f"Available: {', '.join(available) if available else 'none'}")

    venue_dir = TEMPLATES / venue
    copied = []
    for src in sorted(venue_dir.rglob("*")):
        if not src.is_file() or src.name in SKIP:
            continue
        dst = PAPER / src.relative_to(venue_dir)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst.relative_to(ROOT).as_posix())

    if not copied:
        sys.exit(f"{venue_dir} has no files to copy")

    # A paper targets one venue; the catalogue has no purpose after the choice.
    shutil.rmtree(TEMPLATES)

    print(f"[{venue}] initialised. Copied into paper/:")
    for c in copied:
        print(f"  {c}")
    print("Removed templates/")
    print()
    print("Next:")
    print("  1. fill in the title and authors in paper/main.tex")
    print("  2. build: uv run latexmkrc.py")
    print("  (formatting.tex is the venue author guide, kept for reference)")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--init", nargs="?", const="", metavar="VENUE",
                    help="lay out paper/ from templates/<VENUE>, then drop templates/")
    ap.add_argument("--watch", action="store_true", help="rebuild on save")
    ap.add_argument("--clean", action="store_true",
                    help="remove everything the build produced")
    opts = ap.parse_args()

    sys.exit(init(opts.init) if opts.init is not None else build(opts))


if __name__ == "__main__":
    main()
