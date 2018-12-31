Lexical Analysis
================

Pytch source files are encoded in UTF-8.

The compiler takes the source file as input and runs these steps:

* Runs the |lexer|_ to turn the source file into a sequence of |tokens|_.
* Runs the *preparser* to insert dummy tokens which indicate structure inferred
  from the source file's indentation (see Indentation_).
* Runs the |parser|_ to convert the sequence of tokens into a |syntax tree|_.
  This representation is then passed to the rest of the compiler for
  processing.

.. Italicizing a link in RST: https://stackoverflow.com/a/10766650/344643

.. _lexer: https://en.wikipedia.org/wiki/Lexical_analysis
.. |lexer| replace:: *lexer*

.. _tokens: https://en.wikipedia.org/wiki/Lexical_analysis#Token
.. |tokens| replace:: *tokens*

.. _parser: https://en.wikipedia.org/wiki/Parsing#Computer_languages
.. |parser| replace:: *parser*

.. _`syntax tree`: https://en.wikipedia.org/wiki/Abstract_syntax_tree
.. |syntax tree| replace:: *syntax tree*

Maximal munch
-------------

In the case of ambiguity about the lexing of a token or other lexical
element, the interpretation which greedily maximizes the length of that
lexical element is preferred, unless otherwise noted.

For example, ``foobar`` is interpreted as a single `identifier
<Identifiers_>`_, rather than as the identifier ``foo`` followed by the
identifier ``bar`` (or any other partitioning of this identifier).

Whitespace
----------

*Whitespace* is a non-token lexical element used for two purposes:

1. When present at the beginning of a line, to indicate the structure of the
   code by means of `indentation <Indentation_>`_.
2. Elsewhere, to separate tokens for legibility purposes. When used this way,
   multiple consecutive whitespace characters are logically equivalent to a
   single whitespace character.

Whitespace may be either a space character or a newline:

.. code-block:: ebnf

   whitespace-char ::= ' ' | '\n'

Note that other whitespace characters, such as tabs, are not permitted in
Pytch files.

.. design-note::

   For more discussion on why tabs are prohibited, see `this commit message
   <https://github.com/arxanas/pytch/commit/69972bd7d4703e5b0685997bd02baca908584d80>`__.

Comments
--------

*Comments* are non-token lexical elements which are strictly for the
programmer's benefit, and do not affect the generated code. Usually they are
used to document or explain the following piece of code. They can also be
used to temporarily remove a section of code.

They are indicated with a ``#``, which cause the compiler to ignore it and
the rest of the line:

.. code-block:: ebnf

   comment ::= '#' <any character but '\n'>*

This is the same as `in Python
<https://docs.python.org/3/reference/lexical_analysis.html#comments>`__.

Example:

.. code-block:: pytch

   # This is a comment.
   this_is_a_function_call_not_a_comment()  # This is a trailing comment.

Keywords
--------

*Keywords* are words in the source code which have special meaning to the
parser.

This is the current list of keywords in Pytch:

* ``and``
* ``else``
* ``if``
* ``let``
* ``or``
* ``then``

Identifiers
-----------

*Identifiers* are tokens in the source code which logically refer to the name
of a binding. They adhere to the following grammar, with the additional
restriction that they are not a `keyword <Keywords_>`_:

.. code-block:: ebnf

   head-char  ::= 'a'...'z' | 'A'...'Z' | '_'
   tail-char  ::= head-char | '0'...'9'
   identifier ::= head-char tail-char*

Identifiers are case-sensitive.

Examples of legal identifiers:

* ``foo``
* ``FooBar123``
* ``__foo__``

Examples of illegal identifiers:

* ``1foo``
* ``foo_😊``
* ``プログラミング言語``

.. design-note::

   The set of legal identifiers in Pytch is more restrictive than `in Python
   <https://docs.python.org/3/reference/lexical_analysis.html#identifiers>`__
   for now, due to the implementation difficulty. Unicode support for
   identifiers may be implemented in the future.

Indentation
-----------

Pytch is indentation-sensitive, but in a different way than Python. Pytch is
|expression-oriented|_, and a consequence is that expressions may implicitly
span many lines. As a result, the rules for determining the ends of
expressions are different.

.. _`expression-oriented`: https://en.wikipedia.org/wiki/Expression-oriented_programming_language
.. |expression-oriented| replace:: *expression-oriented*

The *preparser* is responsible for converting Pytch source code into an
indentation-insensitive version of the language, which is then processed by
the parser.

.. design-note::

   Pytch's preparser is similar in spirit to F#'s preparser. See the `F# 4.1
   specification <https://fsharp.org/specs/language-spec/>`__, section 15.1
   *Lightweight Syntax* for more details.

   F#'s preparser is more strict than Pytch's, as it emits warnings about
   unexpected indentation. The idea in Pytch is to rely on the autoformatter
   to expose unexpected indentation, while allowing the user to write their
   code in a relatively free-form manner (such as by copying and pasting it).

Dummy tokens
~~~~~~~~~~~~

Consider the following code:

.. code-block:: pytch

   let foo =
     print("calculating foo")
     "foo"
   print("the value of foo is " + foo)

The first ``print`` call and the ``"foo"`` string literal are part of the
``let``-binding's expression, and the second ``print`` call is the body of
the ``let``-expression. During preparsing, the compiler desugars the above by
inserting *dummy tokens*, here denoted in all-caps:

.. code-block:: pytch

   let foo =
     print("calculating foo") SEMICOLON
     "foo"
   IN
   print("the value of foo is " + foo)

The ``SEMICOLON`` binary operator introduces a "statement" expression, in
which the left-hand operand is evaluated and discarded and the right-hand
operand is evaluated and returned. The ``IN`` token is used to separate the
definition of ``foo`` from the expression that uses ``foo``.

Dummy tokens may not be written explicitly by the user.

Indentation stack
~~~~~~~~~~~~~~~~~

The *indentation level* of a token is the number of spaces at the beginning
of the first line containing that token.

The preparser maintains a *indentation stack* whose elements contain the
following information:

* A token kind.
* The indentation level of that token.
* The line number of that token.

The preparser processes tokens sequentially, sometimes pushing token
information onto the above stack or popping entries off, depending on the
details of the token.

Unwinding
~~~~~~~~~

The preparser may trigger *unwinding* when encountering certain tokens. To
unwind, it pops entries off of the indentation stack until the top-most token
meets some condition.

For example, when the preparser encounters a dedented token, it may trigger
unwinding until the top-most token has a lesser or equal indentation level,
or when it encounters a ``)``, it may trigger unwinding until a ``(`` token
popped off.

Certain tokens will emit dummy tokens when popped off of the indentation
stack. For example, ``let`` will emit ``IN`` and ``if`` will emit
``$endif``.

``let``-expressions
~~~~~~~~~~~~~~~~~~~

When encountering a ``let`` token, it is pushed onto the indentation stack.
Once a token with

* the same or lesser indentation level as the ``let``
* and a later line number than the ``let``

is reached, the ``IN`` dummy token is inserted before it to indicate the end
of the ``let``-expression's binding.

Statement-expressions
~~~~~~~~~~~~~~~~~~~~~

When the preparser encounters a new token, if there are no entries on the
indentation stack, or if the top entry

* is on an earlier line
* and has the same indentation level

then the preparser pops the top entry off of the indentation stack and pushes
the current entry.

Brackets
~~~~~~~~

When the preparser encounters an opening bracket token (such as ``(``), it
pushes an entry on the stack for that token, but with indentation level
``0``. (This ensures that the preparser doesn't unwind it when a token inside
the brackets has a lesser indentation level.)

When the preparser encounters a closing bracket token (such as ``)``), it
unwinds to the nearest corresponding opening bracket token and pops it off.

.. _lexical-analysis-literals:

Literals
--------

Integer literals
~~~~~~~~~~~~~~~~

*Integer literals* denote integral values of the ``int`` type:

.. code-block:: ebnf

   digit           ::= '0'...'9'
   integer-literal ::= digit+

Integers in Pytch are arbitrary-precision, so integer literals can be any
length.

Floating-point literals
~~~~~~~~~~~~~~~~~~~~~~~

*Floating-point literals* denote `floating-point numbers
<https://en.wikipedia.org/wiki/Floating-point_arithmetic>`__.

.. todo::

   Implement floating-point literals. Tracked in
   https://github.com/pytch-lang/pytch/issues/27.

String literals
~~~~~~~~~~~~~~~

*String literals* denote `string values
<https://en.wikipedia.org/wiki/String_(computer_science)>`__.

.. code-block:: ebnf

   # In this definition, string-literal-item* does not obey
   # the maximal munch rule. Instead, it matches the shortest
   # possible value.
   string-literal ::= "'" string-literal-item* "'"
                    | '"' string-literal-item* '"'

   string-literal-item ::= string-literal-char
                         | escape-sequence
   string-literal-char ::= <any character but '\' or '\n'>
   escape-sequence     ::= '\' <any character but '\n'>

For example, ``"hello world"`` is a string literal.

.. todo::

   Implement richer types of string literals, such as triple-quoted strings,
   raw strings, or byte-strings.

Operators
---------

.. _lexical-analysis-binary-operators:

Binary operators
~~~~~~~~~~~~~~~~

*Binary operators* are operators that take two expressions as operands:

.. code-block:: ebnf

   binary-operator ::= '+'
                     | '-'
                     | "and"
                     | "or"
                     | SEMICOLON
