r"""
program = toplevel_stmt? (_ toplevel_stmt)* _?
toplevel_stmt = val_stmt / type_stmt / let_stmt

val_stmt = "val" _ ident _ "::" _ type_expr
type_stmt = "type" _ ident _ "=" _ type_expr
type_expr =
  type_expr_atom /
  type_expr_function /
  type_expr_record /
  type_expr_tuple /
  ("(" _ type_expr _ ")")
type_expr_function = type_expr _ ("->" _ type_expr)+
type_expr_record = "{"
  _ type_expr_record_field
  (_ type_expr_record_field  _";")*
  (_ ";")?
_ "}"
type_expr_record_field = ident _ "::" _ type_expr
type_expr_tuple = "(" _ type_expr (_ "," _ type_expr)+ _ ")"
type_expr_atom = ident / poly_ident

let_stmt = let_plain_expr / let_func_expr
let_in_expr = let_stmt _ "in" _ expr
let_plain_expr = "let" _ ident _ "=" _ expr
let_func_expr = "let" _ ident (_ ident)* _ "=" _ expr

expr =
  let_in_expr /
  function_call /
  ident /
  int_literal /
  string_literal

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
