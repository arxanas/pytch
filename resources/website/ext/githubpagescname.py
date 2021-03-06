"""Add the CNAME file to the Github Pages site.

This CNAME file lets Github know what domains point to the documentation.

This extension builds on the functionality offered in the [`githubpages`
extension](https://github.com/sphinx-doc/sphinx/blob/master/sphinx/ext/githubpages.py).
"""
import os
from typing import Any, Dict

import sphinx


def create_cnames(app, env):
    if app.builder.format == "html":
        cnames = app.config["github_pages_cname"]
        if cnames:
            path = os.path.join(app.builder.outdir, "CNAME")
            with open(path, "w") as f:
                # NOTE: don't write a trailing newline. The `CNAME` file that's
                # auto-generated by the Github UI doesn't have one.
                f.write(cnames)


def setup(app) -> Dict[str, Any]:
    app.connect("env-updated", create_cnames)

    # We only allow a single domain for the CNAME, rather than a list of
    # domains, as Github appears to only allow one for now:
    # https://stackoverflow.com/q/16454088
    app.add_config_value("github_pages_cname", "", "html")

    return {"version": sphinx.__display_version__, "parallel_read_safe": True}
