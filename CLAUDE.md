# Working in this repository

This repository holds one paper being written for one conference. Treat it as a
manuscript, not as a software project that happens to contain `.tex` files.

## Git

Do **not** add a `Co-Authored-By: Claude` trailer, a "Generated with Claude Code"
line, or any other attribution to commits, commit messages, or pull request
bodies. Authorship of a paper is a matter of academic record: it belongs to the
people listed in `main.tex` and nobody else. Commit as the repository's
configured user, with a plain message and nothing appended.

## References

**Never write a bibliography entry from memory.** Model recall of citations is
unreliable in a specific and dangerous way: it produces entries that look
correct (plausible authors, a plausible venue, a plausible year) for papers
that do not exist, or attaches a real title to the wrong authors. A fabricated
citation that reaches review is a serious problem for the authors, and it is
invisible in the PDF because it renders exactly like a real one.

So, whenever adding to or editing `references.bib`:

1. Spawn a subagent to verify each entry against arXiv (or the publisher's own
   listing, or the ACL Anthology, whichever applies). Verification means
   retrieving the record, not recognising the name.
2. The subagent must confirm, field by field: the title, the full author list
   and its order, the year, and the venue. Report back the source URL or arXiv
   identifier for each entry it checked.
3. Anything that cannot be confirmed does not go in the file. Say so plainly
   rather than inserting a best guess with a note to check it later: the note
   gets lost, the entry does not.

Use one subagent per batch of entries rather than one per entry, and pass it the
exact `.bib` text to verify so it checks what will actually be committed.

The same care applies to claims about prior work in the body text. Do not
describe what a cited paper did unless its content has actually been read.

## Prose

Write in the register of a published paper, not of documentation or a chat reply.

- Assert findings directly. "The model reaches 82.4 accuracy", not "we can see
  that the model seems to reach around 82.4 accuracy"
- No colloquial or conversational register. Contractions (*don't*, *it's*),
  conversational connectives (*so*, *anyway*, *of course*), rhetorical questions
  addressed to the reader, and exclamation marks do not belong in the
  manuscript. Use the vocabulary and sentence construction of the venue's
  published papers
- No hedging stacks (*may potentially suggest*), no filler openers (*It is
  important to note that*), no first-person narration of the writing process
  (*Now we will discuss*)
- Past tense for what was done and observed, present tense for what holds in
  general and for what the paper itself does
- Define a term once, then use it consistently. Do not alternate synonyms for
  the same concept for variety; in a paper that reads as a distinction
- Quantities carry units and, where the venue expects them, error bars. A number
  without a comparison point is not a result
- Match the surrounding text. Section drafts should be indistinguishable in
  voice from sections already written
- Avoid the em-dash (—). Restructure the sentence, or use a comma, a colon, a
  semicolon, or parentheses instead. The same applies to the en-dash used as
  punctuation; the en-dash remains correct for numeric ranges and compound
  names

## Structure

The sectioning must be systematic and hold to the standard of a top-tier venue.
Each section states one thing and ends where the next begins: the introduction
establishes the problem, the gap in prior work, and the contribution list; the
method is presented before any result that depends on it; the experimental setup
is separated from the analysis of what the experiments showed. A reader should
be able to reconstruct the argument from the section titles alone. Sections
follow the organisation the venue's accepted papers use, not an ad hoc order,
and material that supports rather than carries the argument goes to the
appendix.

- Body sections live in `paper/sections/`, appendices in
  `paper/sections/appendix/`. `main.tex` only imports them
- Figures go in `paper/resources/figures/`, tables in `paper/resources/tables/`
- Do not edit the venue's `.sty`, `.cls`, or `.bst` files. Formatting rules are
  the venue's to set, and altering them is grounds for desk rejection
- `formatting.tex` is the venue's own author guide, kept for reference. It is a
  separate document; it is not part of the manuscript

## Building

`uv run latexmkrc.py`. Artifacts go to `build/`; the finished PDF is copied to
`paper/main.pdf`. Do not add build outputs to git.
