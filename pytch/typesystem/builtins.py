from pytch.containers import PMap, PVector
from .reason import BuiltinReason
from .types import BaseTy, FunctionTy, Ty, TyVar, UniversalTy


ERR_TY = BaseTy(name="<error>", reason=BuiltinReason(name="<error>"))
"""Error type.

Produced when there is a typechecking error, in order to prevent cascading
failure messages.
"""

NONE_TY = BaseTy(name="None", reason=BuiltinReason(name="None"))
"""None type, corresponding to Python's `None` value."""

OBJECT_TY = BaseTy(name="object", reason=BuiltinReason(name="object"))
"""Object type. This is the top type since everything is an object."""

VOID_TY = BaseTy(name="<void>", reason=BuiltinReason(name="<void>"))
"""Void type.

Denotes the lack of a value. The Python runtime has no concept of "void":
functions which don't `return` anything implicitly return `None`.

However, there are some cases where it would be dangerous to allow the user
to return `None` implicitly. For example, implicitly assigning `None` to
`foo` here was probably not intended:

```
let foo =
  if cond()
  then "some value"
```
"""

INT_TY = BaseTy(name="int", reason=BuiltinReason(name="int"))
"""Integer type, corresponding to Python's `int` type."""

top_ty_reason = BuiltinReason(name="<any type>")
top_ty_var = TyVar(name="top_ty", reason=top_ty_reason)
TOP_TY = UniversalTy(quantifier_ty=top_ty_var, ty=top_ty_var, reason=top_ty_reason)
"""The top type.

All types are a subtype of this type, including void. You likely want to use
the `object` type instead.
"""


def _make_print() -> FunctionTy:
    print_reason = BuiltinReason(name="print")
    # TODO: this may have to be some kind of `ArgumentTy` instead, so that it
    # can have its own reason, and so that it can take on a label.
    domain: PVector[Ty] = PVector([OBJECT_TY])
    codomain = NONE_TY
    return FunctionTy(domain=domain, codomain=codomain, reason=print_reason)


# TODO: add the Python builtins to the global scope.
GLOBAL_SCOPE: PMap[str, Ty] = PMap({"None": NONE_TY, "print": _make_print()})
