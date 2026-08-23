# latex-template

A starting point for writing one paper for one conference. Clone this repository
per paper, pick a venue, and write.

- Every build artifact goes to `build/`. `paper/` holds the manuscript and the finished PDF, nothing else
- Only the **contents of `paper/`** are uploaded to Overleaf or a submission site. They compile as-is, with no configuration
- The TeX toolchain is installed inside `.venv`. Nothing is installed system-wide, and deleting `.venv` removes every trace of it

## Requirements

| | Notes |
|---|---|
| **Python 3.9+** | |
| **uv** | `pip install uv`, or see the [installation guide](https://docs.astral.sh/uv/getting-started/installation/) |
| **VS Code + LaTeX Workshop** | Optional. Build on save, PDF preview, source/PDF navigation |

A TeX distribution (MiKTeX, TeX Live, MacTeX) is **not required**. The first build
downloads about 500 MB into `.venv/tinytex`, which takes roughly two minutes. It
bundles its own perl, so there is nothing else to set up.

## Getting started

```bash
git clone <this repository> my-paper
cd my-paper

uv run latexmkrc.py --init          # list available venues
uv run latexmkrc.py --init WACV     # lay out paper/ for a venue
```

Then fill in the title and authors in `paper/main.tex` and write your sections in
`paper/sections/`. Once a venue is chosen, `templates/` can be deleted.

## Building

```bash
uv run latexmkrc.py                 # incremental build
uv run latexmkrc.py --watch         # rebuild on every save (Ctrl+C to stop)
uv run latexmkrc.py --clean         # remove everything the build produced
```

The result is `paper/main.pdf`. Auxiliary files stay in `build/`.

Rebuilds are incremental: editing body text does not re-run bibtex, so a typical
save costs a second or two rather than a full four-pass rebuild.

## VS Code

**Installing the extension** — any of these works.

1. Open this folder in VS Code and accept the "install recommended extensions" prompt
2. Extensions panel (`Ctrl+Shift+X`) → search `LaTeX Workshop` → Install
3. From a terminal: `code --install-extension James-Yu.latex-workshop`

`.vscode/settings.json` is committed, so no further configuration is needed. Once
the extension is installed, saving a `.tex` file rebuilds the paper and refreshes
the preview.

**Useful shortcuts**

| | |
|---|---|
| `Ctrl+Alt+B` | Build |
| `Ctrl+Alt+V` | Open the PDF preview |
| `Ctrl+Alt+J` | Jump from the cursor to that spot in the PDF |
| `Ctrl+click` in the PDF | Jump to the source line that produced it |

The last two are SyncTeX, which needs `paper/main.synctex.gz`. The build copies it
there automatically.

## Layout

```
paper/            The manuscript. Upload the contents of this folder
  main.tex        Entry point, already carrying the venue's document class
  preamble.tex    Packages and macros
  sections/       Body text, plus appendix/
  resources/      figures/, tables/
  references.bib
  *.sty *.bst     The chosen venue's style files
  formatting.tex  The venue's own author guide, kept for reference
  main.pdf        Build result (gitignored)

templates/        Venue catalogue. --init copies one venue in and deletes this
  <venue>/        Exactly what a paper for that venue needs
build/            All auxiliary files (gitignored)
.venv/            Python packages and the TeX toolchain (gitignored)

latexmkrc.py      Build, and --init to pick a venue
latexmkrc         Output paths, bibtex search paths, PDF copy
```

## Adding a venue

`templates/<venue>/` contains exactly the files a paper for that venue needs, and
`--init` copies all of them into `paper/`. Every venue directory follows the same
required layout, which `templates/README.md` specifies in full: the kit's own
`README.md`, a `main.tex` derived from the kit by removing its body, the kit's
original main file kept as `formatting.tex`, `references.bib`, and everything
else preserved as shipped.

Note that `--init` deletes `templates/`, so test a new venue on a scratch clone.

## Troubleshooting

| Symptom | Where to look |
|---|---|
| Build failed | `build/main.log` |
| A package is missing | The build installs it with `tlmgr` automatically; check the message if that fails |
| PDF builds but the bibliography is empty | Check that `\cite` keys match entries in `paper/references.bib` |
