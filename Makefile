.PHONY: all clean

SYNTAX_TREES = pytch/greencst.py pytch/redcst.py
SYNTAX_TREE_SPEC = pytch/syntax_tree.txt

DOCS = docs
DOCS_SOURCE = website

HIGHLIGHTER_SOURCE = resources/syntax-highlighting/pytch-grammar.yaml
HIGHLIGHTER_PYGMENTS_DRIVER = resources/syntax-highlighting/pytchlexer.py.inc
HIGHLIGHTER_PYGMENTS = website/ext/pytchlexer.py
HIGHLIGHTER_VSCODE = resources/syntax-highlighting/pytch.tmLanguage.json

all: $(SYNTAX_TREES) $(DOCS) $(HIGHLIGHTER_PYGMENTS)

pytch/%cst.py: bin/generate_%cst.py $(SYNTAX_TREE_SPEC)
	$< <$(SYNTAX_TREE_SPEC) >$@
	poetry run black $@

# Note: Sphinx will not pick up core changes (e.g. to CSS), so `make clean` has
# to be run manually in that case.
$(DOCS): $(HIGHLIGHTER_PYGMENTS) $(DOCS_SOURCE) $(DOCS_SOURCE)/* $(DOCS_SOURCE)/**/*
	poetry run sphinx-build -b html $(DOCS_SOURCE) $(DOCS)
	touch $(DOCS)

$(HIGHLIGHTER_PYGMENTS): $(HIGHLIGHTER_SOURCE) $(HIGHLIGHTER_PYGMENTS_DRIVER)
	# Sphinx won't rebuild the entire website just because the syntax highlighter
	# changed.
	-rm -r $(DOCS)
	-rm $@

	PYTHONPATH=./resources/syntax-highlighting \
	    python -m piro $(HIGHLIGHTER_SOURCE) -o pygments >$@.tmp
	cat $(HIGHLIGHTER_PYGMENTS_DRIVER) >>$@.tmp

	# Make sure not to generate the syntax highlighter if generation fails.
	mv $@.tmp $@
	poetry run black $@

$(HIGHLIGHTER_VSCODE): $(HIGHLIGHTER_SOURCE)
	PYTHONPATH=./resources/syntax-highlighting \
	    python -m piro $(HIGHLIGHTER_SOURCE) -o vscode >$@.tmp

	# Make sure not to generate the syntax highlighter if generation fails.
	mv $@.tmp $@

clean:
	-rm $(SYNTAX_TREES)
	-rm $(HIGHLIGHTER_PYGMENTS) $(HIGHLIGHTER_PYGMENTS).tmp
	-rm $(HIGHLIGHTER_VSCODE) $(HIGHLIGHTER_VSCODE).tmp
	-rm -r $(DOCS)
