import textwrap
from typing import cast, Dict, List, Mapping, Sequence, Tuple, Union

from piro.parser import ContextRule, Schema, Scope

template = """\
from pygments.lexer import RegexLexer
import pygments.token as token

class {class_name}(RegexLexer):
    name = {lexer_name}
    filenames = {filenames}

    tokens = {{
{tokens}
    }}
"""


PygmentsContextRule = Union[Tuple[str, str], Tuple[str, str, str]]


def compile_pygments(schema: Schema) -> str:
    return template.format(
        class_name=get_class_name(schema),
        lexer_name=get_lexer_name(schema),
        filenames=get_filenames(schema),
        tokens=get_tokens(schema),
    )


def get_class_name(schema: Schema) -> str:
    return schema.metadata.name.capitalize() + "Lexer"


def get_lexer_name(schema: Schema) -> str:
    return repr(schema.metadata.name)


def get_filenames(schema: Schema) -> Sequence[str]:
    return [f"*.{extension}" for extension in schema.metadata.file_extensions]


def get_tokens(schema: Schema) -> str:
    if "root" not in schema.contexts:
        raise ValueError("No context named 'root' provided")

    pygments_context_rules: Dict[str, Sequence[PygmentsContextRule]] = {}
    for context_name, context_rules in schema.contexts.items():
        pygments_context_rules.update(
            get_pygments_context_rules(
                schema=schema, context_name=context_name, context_rules=context_rules
            )
        )

    result = ""
    for scope_name, scope_rules in pygments_context_rules.items():
        result += f"{scope_name!r}: [\n"
        for rule in scope_rules:
            if len(rule) == 2:
                rule = cast(Tuple[str, str], rule)
                (regex, scope) = rule
                result += f"    ({regex!r}, {scope}),\n"
            elif len(rule) == 3:
                rule = cast(Tuple[str, str, str], rule)
                (regex, scope, new_state) = rule
                result += f"    ({regex!r}, {scope}, {new_state!r}),\n"
            else:
                assert False, f"Unexpected rule type (length is {len(rule)}): {rule!r}"
        result += f"],\n"
    result = result.strip()
    return textwrap.indent(result, prefix=(" " * 8))


def get_pygments_context_rules(
    schema: Schema, context_name: str, context_rules: Sequence[ContextRule]
) -> Mapping[str, Sequence[PygmentsContextRule]]:
    result: Dict[str, Sequence[PygmentsContextRule]] = {}
    temp_context_num = 0
    pygments_context_rules: List[PygmentsContextRule] = []
    for rule in context_rules:
        scope = schema.get_scope(rule.scope_name, context_name=context_name)
        begin_and_end = rule.begin_and_end
        if begin_and_end is None:
            pygments_context_rules.append((rule.regex, get_pygments_scope_name(scope)))
        else:
            begin_rule = begin_and_end[0]
            inner_scope = schema.get_scope(
                begin_rule.scope_name, context_name=context_name
            )

            end_rule = begin_and_end[1]
            end_rule_scope = schema.get_scope(
                end_rule.scope_name, context_name=context_name
            )

            subcontext_name = f"{rule.scope_name}__{temp_context_num}"
            temp_context_num += 1
            assert subcontext_name not in result

            pygments_context_rules.append(
                (begin_rule.regex, get_pygments_scope_name(scope), subcontext_name)
            )
            result[subcontext_name] = [
                (rule.regex, get_pygments_scope_name(inner_scope)),
                (end_rule.regex, get_pygments_scope_name(end_rule_scope), "#pop"),
            ]
    result[context_name] = pygments_context_rules
    return result


def get_pygments_scope_name(scope: Scope) -> str:
    return f"token.{scope.pygments}"
