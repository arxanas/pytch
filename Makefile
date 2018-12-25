.PHONY: all clean

SYNTAX_TREES = pytch/greencst.py pytch/redcst.py
SYNTAX_TREE_SPEC = pytch/syntax_tree.txt

DOCS = docs
DOCS_SOURCE = website

all: $(SYNTAX_TREES) $(DOCS)

pytch/%cst.py: bin/generate_%cst.py $(SYNTAX_TREE_SPEC)
	$< <$(SYNTAX_TREE_SPEC) >$@
	poetry run black $@

# Note: Sphinx will not pick up core changes (e.g. to CSS), so `make clean` has
# to be run manually in that case.
$(DOCS): $(DOCS_SOURCE) $(DOCS_SOURCE)/* $(DOCS_SOURCE)/**/*
	poetry run sphinx-build -b html $(DOCS_SOURCE) $(DOCS)
	touch $(DOCS)

clean:
	-rm $(SYNTAX_TREES)
	rm -rf $(DOCS)
