import json
from typing import Any, Mapping

from piro.parser import Schema


def compile_vscode(schema: Schema) -> str:
    root_scope_name = next(iter(schema.contexts.keys()))
    payload = {
        "$schema": "https://raw.githubusercontent.com/martinring/tmlanguage/master/tmlanguage.json",
        "name": schema.metadata.name,
        "scopeName": f"source.{schema.metadata.name}",
        "fileTypes": schema.metadata.file_extensions,
        "patterns": [{"include": f"#{root_scope_name}"}],
        "repository": compile_contexts(schema),
    }
    return json.dumps(payload, indent=4)  # pretty-print the JSON


def compile_contexts(schema: Schema) -> Mapping[str, Any]:
    result = {}
    for context_name, context_rules in schema.contexts.items():
        patterns = []
        for context_rule in context_rules:
            pattern: Mapping[str, Any]
            begin_and_end = context_rule.begin_and_end
            if begin_and_end is None:
                pattern = {
                    "match": context_rule.regex,
                    "name": schema.get_scope(
                        context_rule.scope_name, context_name
                    ).vscode
                    + ".pytch",
                }
            else:
                (begin, end) = begin_and_end
                pattern = {
                    "begin": begin.regex,
                    "end": end.regex,
                    "name": schema.get_scope(
                        context_rule.scope_name, context_name
                    ).vscode
                    + ".pytch",
                    "patterns": [
                        {
                            "match": context_rule.regex,
                            "name": schema.get_scope(
                                context_rule.scope_name, context_name
                            ).vscode
                            + ".pytch",
                        }
                    ],
                }
            patterns.append(pattern)
        result[context_name] = {"patterns": patterns}
    return result
