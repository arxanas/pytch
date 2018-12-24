.PHONY: all

all: pytch/greencst.py pytch/redcst.py docs

pytch/greencst.py pytch/redcst.py: pytch/syntax_tree.txt
	./bin/generate_syntax_trees.sh

docs: website/conf.py website/*.rst website/**/*.rst
	./bin/generate-docs.sh
