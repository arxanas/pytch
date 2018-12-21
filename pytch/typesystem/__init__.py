"""Type inference and typechecking.

The Pytch type system is a bidirectional typechecking system, based off of
the system described in [Dunfield 2013] (see Figures 9-11 for the algorithmic
typing rules for the system). A standard Hindley-Milner type system would be
difficult to reconcile in the presence of subtyping, which will naturally
occur when interfacing with Python code.

  [Dunfield 2013]: https://www.cl.cam.ac.uk/~nk480/bidir.pdf

Terminology used in this module:

  * `ty`: "type".
  * `ctx`: "context".
  * `env`: "environment". This only refers to the usual sort of global
  configuration that's passed around, rather than a typing environment (Γ),
  which is called a "context" instead.
  * `var`: "variable", specifically a type variable of some sort.
  * The spelling "judgment" is preferred over "judgement".

"""
from .typecheck import Typeation, typecheck

__all__ = ["Typeation", "typecheck"]
