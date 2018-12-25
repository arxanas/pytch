Getting Started
===============

Installation
------------

Pytch is currently written in Python 3.7. To install Pytch, run::

    pip install pytch

Running a Pytch script
----------------------

Create the file ``helloworld.pytch`` with this content:

.. code-block:: pytch

   print("Hello, world!")

Then run the ``pytch run`` command::

    pytch run path/to/file.pytch

It should produce this output::

    Hello, world!

Launching the REPL
------------------

You can try out features interactively by launching the `REPL
<https://en.wikipedia.org/wiki/Read%E2%80%93eval%E2%80%93print_loop>`_ with
``pytch repl``::

    $ pytch repl
    Pytch version 0.0.1 REPL
    >>> print("Hello, world!")
    ...
    Hello, world!
    >>>
