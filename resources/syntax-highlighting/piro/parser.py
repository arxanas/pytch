import re
from typing import Any, List, Mapping, Optional, Sequence, Tuple

import attr


@attr.s(auto_attribs=True, frozen=True)
class Metadata:
    name: str
    file_extensions: List[str]


@attr.s(auto_attribs=True, frozen=True)
class Scope:
    vscode: str
    pygments: str


@attr.s(auto_attribs=True, frozen=True)
class ContextRule:
    regex: str
    scope_name: str
    begin_and_end: Optional[Tuple["ContextRule", "ContextRule"]]


@attr.s(auto_attribs=True, frozen=True)
class Schema:
    metadata: Metadata
    scopes: Mapping[str, Scope]
    contexts: Mapping[str, Sequence[ContextRule]]

    def get_scope(self, scope_name: str, context_name: str) -> Scope:
        try:
            return self.scopes[scope_name]
        except KeyError as e:
            raise ValueError(
                f"Unknown scope {scope_name!r} for context {context_name!r}"
            ) from e


InputData = Mapping[str, Any]


def parse(input_data: InputData) -> Schema:
    # This could probably all be replaced with some sort of data validation
    # library.
    metadata = parse_metadata(input_data)
    scopes = parse_scopes(input_data)
    contexts = parse_contexts(input_data)
    return Schema(metadata=metadata, scopes=scopes, contexts=contexts)


def parse_metadata(input_data: InputData) -> Metadata:
    name = input_data["name"]
    file_extensions = input_data["file_extensions"]
    return Metadata(name=name, file_extensions=file_extensions)


def parse_scopes(input_data: InputData) -> Mapping[str, Scope]:
    scopes = {}
    for scope_name, scope_data in input_data.get("scopes", {}).items():
        vscode_scope = scope_data["vscode"]
        pygments_scope = scope_data["pygments"]
        scopes[scope_name] = Scope(vscode=vscode_scope, pygments=pygments_scope)
    return scopes


def parse_contexts(input_data: InputData) -> Mapping[str, Sequence[ContextRule]]:
    contexts = {}
    for context_name, context_data in input_data.get("contexts", {}).items():
        context_rules = []
        for context_rule_data in context_data:
            context_rules.append(parse_context_rule(context_rule_data))
        contexts[context_name] = context_rules
    return contexts


def parse_context_rule(rule_data: Mapping[str, Any]) -> ContextRule:
    scope_name = rule_data["scope"]
    scope_regex = parse_regex(rule_data["regex"])
    begin_and_end: Optional[Tuple[ContextRule, ContextRule]]
    if "begin" in rule_data:
        begin = parse_context_rule(rule_data["begin"])
        end = parse_context_rule(rule_data["end"])
        begin_and_end = (begin, end)
    else:
        begin_and_end = None
    return ContextRule(
        scope_name=scope_name, regex=scope_regex, begin_and_end=begin_and_end
    )


def parse_regex(regex: str) -> str:
    """Simulate re.VERBOSE mode, since not all regex backends support it.

    This just removes whitespace from the regex.
    """
    return re.sub(r"\s+", "", regex)
