# Intro

I once started writing a GUI application in Python -- my first "real",
user-facing application. Then I got a job working in OCaml and suddenly missed
having static typing, type inference, variants, pattern matching, and partial
application in Python.

I couldn't just switch to OCaml, because I needed some Python libraries.  So I
decided that instead of writing my application in Python, I would write a
different programming language to write my application in that has all of those
features, but also strong interop with Python.

# Design

Pytch (pronounced "pitch") is a language that's meant to feel like a
statically-typed ML-style language, while still being able to interoperate with
the wealth of libraries written in Python.

Constraints:

  * Must compile to readable Python (for debugging).
  * Resulting program may have a runtime dependency on Pytch.

Goals:

  * Be able to import Python libraries with a minimum of fuss, while still
    maintaining static type-safety where possible.
  * Focus on pragmatism over purity.
  * Support local type inference.
  * Support algebraic data types and pattern matching.
  * Should be not very much slower than Python, if at all.

Non-goals:

  * To be OCaml or Haskell. Those languages aren't necessarily suited to
    interoperate with a dynamically-typed language like Python.
  * Source-level compatibility with Python. That is, valid Python code need not
    be valid Pytch code.
