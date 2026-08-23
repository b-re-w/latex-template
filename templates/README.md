# Venue templates

A catalogue of conference templates. `--init` copies one of these directories
over `paper/` and then deletes this whole folder: a paper targets one venue, so
the catalogue has no purpose once the choice is made.

```
uv run latexmkrc.py --init          # list what is available
uv run latexmkrc.py --init WACV     # copy templates/WACV into paper/, drop templates/
```

Everything in a venue directory is copied into `paper/`, **except `README.md`**,
which documents the template rather than being part of the paper.

## Required layout

Every venue directory follows the same shape, so that switching the catalogue
entry is the only thing that differs between venues.

| File | Rule |
|---|---|
| `README.md` | The kit's own README, kept verbatim. If the kit ships none, write one naming the template and its year. Not copied into `paper/`. |
| `main.tex` | The venue's main file, adjusted so that once it sits in `paper/` it pulls in `sections/`. See below. |
| `formatting.tex` | The kit's original main file, kept as-is. These files are author guides, so keeping them compilable lets you consult the venue's own formatting rules while writing. |
| `references.bib` | The kit's bibliography, renamed (`custom.bib`, `main.bib`, `example_paper.bib`, …). If the kit ships none, an empty file. |
| `preamble.tex` | Always present. The author's own space for extra packages and drafting macros. If the kit ships one, keep it as-is; if not, add one and wire `\input{preamble}` into `main.tex` at the point the venue's style expects preamble additions. Declare macros with `\providecommand` so they yield to a venue that already defines the same name. |
| everything else | Preserved as shipped: `.sty`, `.cls`, `.bst`, extra guides, rebuttal templates, and so on. |

## What `main.tex` must do

`main.tex` is the kit's own main file with its body removed, not a rewrite. The
preamble is left untouched, so the venue's package list, options and formatting
switches survive exactly as published. Only four things change:

1. The example title becomes a placeholder. The author block keeps the kit's
   structure and comments.
2. The body prose is replaced by the section imports:

   ```latex
   \input{sections/00_abstract}
   \input{sections/01_introduction}
   \input{sections/02_related_work}
   \input{sections/03_method}
   \input{sections/04_experiments}
   \input{sections/05_conclusion}
   ```

3. The bibliography points at `references`, keeping the venue's own
   `\bibliographystyle`.
4. The appendix pulls in `sections/appendix/a_details`.

## Figures

Figures shipped with a kit are **not** kept here. They are moved to
`paper/resources/figures/` up front and renamed `<venue>_<original name>`, for
example `fig1.png` from the IEEE kit becomes `ieee_fig1.png`. The references
inside `formatting.tex` are rewritten to match, so the author guide still renders
once it lands in `paper/`. The prefix keeps two kits from colliding on a name as
generic as `fig1.png`.

If a file already starts with the venue name, leave it alone rather than
doubling the prefix: ICML's `icml_numpapers.pdf` stays `icml_numpapers.pdf`.

## Adding a venue

1. Create `templates/<VENUE>/` and unpack the official kit into it.
2. Rename the kit's main file to `formatting.tex` and its bibliography to
   `references.bib`.
3. Derive `main.tex` from `formatting.tex` by the subtraction above.
4. Move any figures to `paper/resources/figures/` with the venue prefix and fix
   the references in `formatting.tex`.
5. Keep or write `README.md`.
6. Check it: `uv run latexmkrc.py --init <VENUE>` followed by a build.
   Do this on a scratch clone, since `--init` deletes this folder.

## Updating for a new year

Unpack the new kit, then redo steps 2–4. The preamble is the part that changes
between years, and because `main.tex` is a subtraction rather than a rewrite,
comparing the new `formatting.tex` against the previous `main.tex` shows exactly
what needs carrying over.
