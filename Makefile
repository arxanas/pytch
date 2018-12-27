.PHONY: all clean

SYNTAX_TREES = pytch/greencst.py pytch/redcst.py
DOCS = docs

all: $(SYNTAX_TREES) $(DOCS)

$(SYNTAX_TREES): pytch/syntax_tree.txt bin/generate_greencst.py bin/generate_redcst.py bin/generate_syntax_trees.sh
	./bin/generate_syntax_trees.sh

# Note: Sphinx will not pick up core changes (e.g. to CSS), so `make clean` has
# to be run manually in that case.
$(DOCS): website website/* website/**/*
	./bin/generate-docs.sh
	touch $(DOCS)

clean:
	rm $(SYNTAX_TREES)
	rm -rf $(DOCS)
