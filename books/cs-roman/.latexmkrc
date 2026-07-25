# latexmk config for books/cs-roman (run from this directory)
$pdf_mode = 4;  # LuaLaTeX
$lualatex = 'lualatex -interaction=nonstopmode -halt-on-error %O %S';
$out_dir = 'build/aux';
$aux_dir = 'build/aux';
ensure_path('TEXINPUTS', './');
ensure_path('TEXINPUTS', './shared//');
ensure_path('TEXINPUTS', './volumes//');
