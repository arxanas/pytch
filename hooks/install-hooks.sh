#!/bin/sh
set -e
cd "$(git rev-parse --show-toplevel)"
cp ./hooks/pre-commit ./.git/hooks/
