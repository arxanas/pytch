Expressions
===========

Pytch is an |expression-oriented|_ language, so nearly all syntactic elements
are expressions or parts of expressions.

.. _`expression-oriented`: https://en.wikipedia.org/wiki/Expression-oriented_programming_language
.. |expression-oriented| replace:: *expression-oriented*

Some tokens are inserted by the preparser. These tokens are denoted in
all-caps, such as ``SEMICOLON``.

These are the possible expressions:

.. code-block:: ebnf

   expr ::= binary-expr
          | function-call-expr
          | if-expr
          | let-expr
          | literal-expr

Binary expressions
------------------

Binary expressions consist of two operands separated by a :ref:`binary
operator <lexical-analysis-binary-operators>`:

.. code-block:: ebnf

   binary-expr ::= expr binary-operator expr

The result of a binary expression is the result of evaluating the left-hand
operand, then the right-hand operand, then applying the operator to both.

The meanings of the operators are as follows:

* ``SEMICOLON``: Discard left-hand operand and return right-hand operand. Due
  to its sequencing behavior, the ``SEMICOLON`` operator may be considered
  to introduce a *statement expression*.
* All others: same as in Python.

Operator precedence
~~~~~~~~~~~~~~~~~~~

The operators have the following `precedences
<https://en.wikipedia.org/wiki/Order_of_operations>`__ and `associativities
<https://en.wikipedia.org/wiki/Operator_associativity>`__, indicated from
lowest precedence (least binding) to highest precedence (most binding):

+----------------+---------------+
| Operator       | Associativity |
+================+===============+
| ``SEMICOLON``  | Right         |
+----------------+---------------+
| ``or``         | Left          |
+----------------+---------------+
| ``and``        | Left          |
+----------------+---------------+
| ``+``, ``-``   | Left          |
+----------------+---------------+

Function call expressions
-------------------------

Function calls consist of a callee and any number of arguments:

.. code-block:: ebnf

   function-call-expr ::= expr '(' argument-list ')'
   argument-list      ::= argument (',' argument)* [',']
   argument           ::= expr

The result of a function call expression is the result of evaluating the
callee expression, then evaluating each argument expression from left to
right, and then calling the callee expression with the given arguments.

.. todo::

   Implement keyword arguments and splats.

``if``-expressions
------------------

``if``-expressions consist of a condition, a ``then``-clause, and optionally
an ``else``-clause:

.. code-block:: ebnf

   if-expr ::= "if" expr "then" expr ["else" expr]

The result of an ``if``-expression is the result of evaluating the condition;
then, if the condition is truthy, evaluating en``-clause and
returning the result, or otherwise evaluating the ``else``-clause and
returning the result.

Exactly one of the clauses will be evaluated.

In the event that the ``else``-clause is absent, the ``if``-expression is
considered to return a "void" result, the value of which is indeterminate. It
should be used with the statement expression, so that the resulting value is
thrown away.

``let``-expressions
-------------------

``let``-expressions consist of a pattern, a value, and sometimes a body.

.. code-block:: ebnf

   let-expr ::= "let" pattern '=' expr [IN expr]
   pattern  ::= identifier

The result of a ``let``-expression is determined by evaluating the value
expression and binding it to the pattern. Variables bound this way are then
available for use in the body expression. The result of the
``let``-expression is the result of evaluating the body with the new bindings
now in scope.

The body of the ``let``-expression is required, except for at the top-level
of a module, in which case it is optional. In that case, the pattern is bound
and made available as an export of the module.

.. todo::

   Implement support for patterns other than identifier patterns.

Literal expressions
-------------------

Literal expressions consist directly of a lexed :ref:`literal
<lexical-analysis-literals>`:

.. code-block:: ebnf

   literal-expr ::= integer-literal
                  | string-literal

Their values correspond to the value written in the source code.
