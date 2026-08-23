# ---------------------------------------------------------------
# Local build configuration.
#
#   * Every artifact goes to <repo>/build/, so paper/ stays clean.
#   * Redirecting the output also moves bibtex's working directory,
#     so paper/ must be added to its search path or the .bst and .bib
#     files sitting next to main.tex are not found.
#
# This file is a local convenience only. paper/ builds without it,
# exactly as it does on Overleaf:
#     cd paper && latexmk main.tex
# ---------------------------------------------------------------
use Cwd qw(abs_path);

# msys/cygwin perl reports POSIX paths (/c/...) that MiKTeX cannot read.
# Convert them back to native Windows paths (C:/...).
sub win_path {
    my ($p) = @_;
    $p =~ s{^/cygdrive/([A-Za-z])/}{\u$1:/};
    $p =~ s{^/([A-Za-z])/}{\u$1:/};
    return $p;
}

# Walk up from the current directory to the repository root, so this works
# whether latexmk is invoked from the root or from inside paper/.
my $root = win_path(abs_path('.'));
{
    my $d = $root;
    for (1..6) {
        if (-e "$d/paper/main.tex") { $root = win_path($d); last; }
        $d = win_path(abs_path("$d/.."));
    }
}

my $sep = ($root =~ /^[A-Za-z]:/) ? ';' : ':';

$out_dir = "$root/build";
$aux_dir = "$root/build";

# bibtex runs in build/, so point it back at paper/
for my $var ('BSTINPUTS', 'BIBINPUTS') {
    $ENV{$var} = "$root/paper" . $sep . ($ENV{$var} // '') . $sep;
}

$pdf_mode   = 1;    # pdflatex
$bibtex_use = 2;    # run bibtex; also clean .bbl on cleanup
$recorder   = 1;    # write .fls, which is what makes rebuilds incremental
$max_repeat = 5;

# Extensions latexmk does not know about on its own.
# brf comes from hyperref's pagebackref option, which the WACV style enables.
$clean_ext = 'brf';
$pdflatex = 'pdflatex -synctex=1 -interaction=nonstopmode -file-line-error %O %S';

# Copy the build results that belong next to the sources: the finished PDF,
# and the SyncTeX map that lets the editor jump between source and PDF.
# Everything else stays in build/. Both are gitignored.
# Using latexmk's success hook (rather than doing it in build.py) means this
# also fires on every successful rebuild in -pvc / watch mode.
$success_cmd = 'internal copy_final_pdf %D';

sub copy_final_pdf {
    my ($pdf) = @_;
    use File::Copy qw(copy);

    copy($pdf, "$root/paper/main.pdf")
        or warn "could not copy $pdf to paper/main.pdf: $!\n";

    # The viewer looks for the SyncTeX file beside the PDF, so it has to follow.
    my $synctex = $pdf;
    $synctex =~ s/\.pdf$/.synctex.gz/;
    if (-e $synctex) {
        copy($synctex, "$root/paper/main.synctex.gz")
            or warn "could not copy $synctex to paper/: $!\n";
    }
    return 0;
}
