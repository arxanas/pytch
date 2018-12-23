#!/bin/bash
set -euo pipefail

poetry run sphinx-build -b html website docs
