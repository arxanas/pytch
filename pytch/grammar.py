from pyparsing import (
    dblQuotedString,
    FollowedBy,
    Forward,
    Group,
    Keyword,
    lineStart,
    Literal,
    Optional,
    Or,
    ParserElement,
    pyparsing_common,
    pythonStyleComment,
    Suppress,
    ZeroOrMore,
)

from .ast import (
    FunctionCallExpr,
    FunctionTypeExpr,
    Ident,
    IntLiteral,
    LetFuncStmt,
    LetInExpr,
    LetPlainStmt,
    Program,
    RecordTypeExpr,
    StringLiteral,
    TupleTypeExpr,
    TypeExprAtom,
    TypeStmt,
    ValStmt,
)

ParserElement.enablePackrat()


############
#  TOKENS  #
############


t_in = Keyword("in")
t_let = Keyword("let")
t_type = Keyword("type")
t_val = Keyword("val")
keywords = [t_in, t_let, t_type, t_val]

t_arrow = Literal("->")
t_comma = Literal(",")
t_dcolon = Literal("::")
t_equals = Literal("=")
t_lbrace = Literal("{")
t_lparen = Literal("(")
t_rbrace = Literal("}")
t_rparen = Literal(")")
t_squote = Literal("'")


#############
#  HELPERS  #
#############


def delimited_list(element, delim, min=1):
    """Denotes a list delimited by a given token.

    Similar to PyParsing's `delimitedList`, but always looks ahead of the
    delimiter to make sure that there is another of the element type following
    it.

    This might not actually be better than `delimitedList`, but I'm not sure.
    """
    # We have (min - 1) or more delimited elements plus 1 trailing element.
    min -= 1
    return (
        # Use '+' after delimiter, because sometimes we want to allow a
        # trailing delimiter but not require that another element follow it.
        ((element + Suppress(delim) + FollowedBy(element)) * (min,)) - element
    )


#############
#  GRAMMAR  #
#############


comment = pythonStyleComment

string_literal = dblQuotedString
string_literal.setParseAction(StringLiteral)

# TODO: Handle both int literals and float literals.
number_literal = pyparsing_common.number
number_literal.setParseAction(IntLiteral)

# Note that `~Or` doesn't advance the cursor.
ident = ~Or(keywords) + pyparsing_common.identifier
ident.setParseAction(Ident)
poly_ident = Suppress(t_squote) - ident

expr = Forward()


def let_parse_action(text, location, tokens):
    if len(tokens) == 2:
        return LetPlainStmt(text, location, tokens)
    else:
        assert len(tokens) > 2
        return LetFuncStmt(text, location, tokens)


let_stmt = (
    Suppress(t_let) - ident - ZeroOrMore(ident) - Suppress(t_equals) - expr
)
let_stmt.setParseAction(let_parse_action).setName("let statement")
let_in_expr = ~lineStart + (let_stmt - Suppress(t_in) - expr)
let_in_expr.setParseAction(LetInExpr).setName("let-in expression")

non_function_call_expr = (
    let_in_expr |
    ident |
    number_literal |
    string_literal |
    Suppress(t_lparen) - expr - Suppress(t_rparen)
)
function_call_expr = non_function_call_expr * (2,)
function_call_expr.setParseAction(FunctionCallExpr).setName("function call")

expr << (function_call_expr | non_function_call_expr)
expr.setName("expression")

type_expr_atom = ident | poly_ident
type_expr_atom.setParseAction(TypeExprAtom).setName("type name")
type_expr = Forward()
record_field = Group(ident - Suppress(t_dcolon) - type_expr)
record_type_expr = (
    Suppress(t_lbrace) -
    delimited_list(record_field, t_comma) -
    Suppress(Optional(t_comma)) -
    Suppress(t_rbrace)
)
record_type_expr.setParseAction(RecordTypeExpr).setName("record type")
tuple_type_expr = (
    Suppress(t_lparen) +
    delimited_list(type_expr, t_comma, min=2) -
    Suppress(Optional(t_comma)) -
    Suppress(t_rparen)
)
tuple_type_expr.setParseAction(TupleTypeExpr).setName("tuple type")
non_function_type_expr = (
    type_expr_atom |
    record_type_expr |
    tuple_type_expr |
    Suppress(t_lparen) - type_expr - Suppress(t_rparen)
)
function_type_expr = delimited_list(non_function_type_expr, t_arrow, min=2)
function_type_expr.setParseAction(FunctionTypeExpr).setName("function type")
type_expr << (function_type_expr | non_function_type_expr)
type_expr.setName("type expression")

val_stmt = Suppress(t_val) - ident - Suppress(t_dcolon) - type_expr
val_stmt.setParseAction(ValStmt).setName("val declaration")
type_stmt = Suppress(t_type) - ident - Suppress(t_equals) - type_expr
type_stmt.setParseAction(TypeStmt).setName("type declaration")

top_level_stmt = val_stmt | type_stmt | let_stmt
top_level_stmt.setName("top-level statement")
program = ZeroOrMore(top_level_stmt)
program.setParseAction(Program).setName("program")
program.ignore(comment)


#############
#  EXPORTS  #
#############


def parse(contents):
    nodes = program.parseString(contents, parseAll=True)
    assert len(nodes) == 1, "Number of `Program` nodes in parse tree != 1"
    return nodes[0]
