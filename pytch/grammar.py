r"""
program = toplevel_stmt? (_ toplevel_stmt)* _?
toplevel_stmt = val_stmt / let_stmt

val_stmt = "val" _ ident _ ":" _ type_sig
type_sig = type_decl _ ("->" _ type_decl)*
type_decl = ident / poly_ident / ("(" type_sig ")")

let_stmt = plain_let_stmt / func_let_stmt
plain_let_stmt = "let" _ ident _ "=" _ expr
func_let_stmt = "let" _ ident (_ ident)* _ "=" _ expr

expr = (
  function_call /
  ident /
  int_literal /
  string_literal
)

int_literal = ~r"[0-9]+"

string_literal = "\"" string_contents "\""
string_contents = (escaped_char / char)*
escaped_char = "\\" ~r"."
char = ~r"[^\"]"

function_call = ident (_ expr)+

keyword = (~r"\bval\b" / ~r"\blet\b" / ~r"\bin\b")
ident = !keyword ~r"[a-zA-Z_][a-zA-Z_0-9]*"
poly_ident = "'" ident

_ = meaninglessness*
meaninglessness = ~r"\s+" / comment
comment = ~r"#[^\r\n]*"
"""
from parsimonious.grammar import Grammar
grammar = Grammar(__doc__)
