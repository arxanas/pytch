Pytch: tooling-focused Python
=============================

Pytch is an expression-oriented, tooling-focused language that compiles down
to Python. It's a little bit like Kotlin_ or TypeScript_, but for Python.

.. _TypeScript: http://www.typescriptlang.org/
.. _Kotlin: https://kotlinlang.org/

Why Pytch?
----------

Python is a great general-purpose language, but its dynamic nature can make
it hard to get reliable IDE support (such as autocomplete or
go-to-definition) as your project grows.

Pytch is a new programming language designed from the ground up to provide
high-quality IDE support. You can incrementally adopt it into your projects
and start getting better IDE support today.

Pytch also features a `type inference
<https://en.wikipedia.org/wiki/Type_inference>`__ engine, which can help you
catch bugs without writing mounds of tedious type annotations. For example,
it can automatically track where a variable may be ``None`` and warn you if
you didn't handle that case.

Status
------

Unfortunately, Pytch isn't yet usable. You can follow development at `the
issue tracker <https://github.com/arxanas/pytch/projects>`__.

.. toctree::
   :hidden:

   about
   getting-started
   language-reference
   Repository <https://github.com/arxanas/pytch>
