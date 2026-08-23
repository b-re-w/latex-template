#!/usr/bin/env python3
"""Build paper/main.tex. All artifacts go to build/.

    uv run build.py             incremental build
    uv run build.py --watch     rebuild on save
    uv run build.py --clean     remove auxiliary files

The TeX toolchain lives in .venv/tinytex and is installed on first use, so
nothing is installed system-wide and deleting .venv removes every trace of it.
"""
import argparse
import os
import shutil
import subprocess
import tempfile
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEXDIR = ROOT / ".venv" / "tinytex"


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


def package_visible(pkg, binpath, env):
    """True once TeX can actually resolve a file from the package."""
    for ext in (".sty", ".cls"):
        result = subprocess.run([tool("kpsewhich", binpath), pkg + ext],
                                env=env, capture_output=True, text=True)
        if result.stdout.strip():
            return True
    return False


def install_packages(packages, binpath, env):
    """Install CTAN packages with tlmgr and wait until TeX can see them.

    On Windows `tlmgr update --self` hands the infrastructure swap to a
    detached batch file and returns early, so a command issued right after it
    can race with the update. Rather than guessing a delay, poll until the
    package actually resolves.
    """
    for pkg in packages:
        for _ in range(8):
            result = subprocess.run([tool("tlmgr", binpath), "install", pkg],
                                    env=env, capture_output=True, text=True)
            if "needs to be updated" in (result.stdout + result.stderr):
                subprocess.run([tool("tlmgr", binpath), "update", "--self"],
                               env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                time.sleep(2)
                continue

            # Refresh the filename database so new files become visible.
            subprocess.run([tool("mktexlsr", binpath)], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if package_visible(pkg, binpath, env):
                break
            time.sleep(2)
        else:
            print(f"warning: {pkg} could not be installed", file=sys.stderr)


def missing_packages(logfile):
    """Package names reported as missing in a build log."""
    if not logfile.exists():
        return []
    names = []
    for line in logfile.read_text(encoding="utf-8", errors="replace").splitlines():
        if "File `" in line and "' not found" in line:
            name = line.split("File `", 1)[1].split("'", 1)[0]
            if name.endswith((".sty", ".cls")):
                names.append(name.rsplit(".", 1)[0])
    return sorted(set(names))


def run_latexmk(extra, env, binpath, force=False):
    """Run latexmk in paper/.

    latexmk remembers a failed run and refuses to repeat it, so a retry after
    installing the package that caused the failure needs -g to force it.
    """
    args = [tool("latexmk", binpath), "-r", str(ROOT / "latexmkrc")]
    if force:
        args.append("-g")
    args += extra + ["main.tex"]
    return subprocess.run(args, cwd=ROOT / "paper", env=env).returncode


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--watch", action="store_true", help="rebuild on save")
    ap.add_argument("--clean", action="store_true", help="remove everything the build produced")
    opts = ap.parse_args()

    binpath = tex_bin_dir() or install_tex()
    env = tex_env(binpath)

    # -C removes the PDF too, so --clean and the copied paper/main.pdf agree.
    extra = (["-C"] if opts.clean else []) + (["-pvc"] if opts.watch else [])
    code = run_latexmk(extra, env, binpath)

    if opts.clean:
        # latexmk only knows about build/; the copies are ours to remove.
        for name in ("main.pdf", "main.synctex.gz"):
            (ROOT / "paper" / name).unlink(missing_ok=True)

    # TinyTeX ships a fixed package set and does not fetch what is missing.
    # pdflatex stops at the first missing file, so each round reveals at most
    # one more package; keep installing and rebuilding until nothing is left.
    seen = set()
    while code != 0 and not opts.clean:
        missing = [p for p in missing_packages(ROOT / "build" / "main.log")
                   if p not in seen]
        if not missing:
            break
        seen.update(missing)
        print(f"Installing missing packages: {', '.join(missing)}", flush=True)
        install_packages(missing, binpath, env)
        code = run_latexmk(extra, env, binpath, force=True)

    # latexmkrc copies the finished PDF here on success.
    pdf = ROOT / "paper" / "main.pdf"
    if code == 0 and not opts.clean and pdf.exists():
        print(f"PDF: {pdf}")
    sys.exit(code)


if __name__ == "__main__":
    main()
