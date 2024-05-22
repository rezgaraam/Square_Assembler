"""
Ivy is a lightweight software bus for quick-prototyping protocols. It
allows applications to broadcast information through text messages, with a
subscription mechanism based on regular expressions.

If you're used to the standard Ivy API, you probably want to look at the
`std_api` module.

For an introduction of the package, see the :doc:`overview` and the :doc:`tutorial`..


Understanding the package
-------------------------

This Ivy package is made of two modules: :py:mod:`ivy.std_api` and :py:mod:`ivy.ivy`.

In order to understand the way it works, we highly suggest that you read the
materials available from the `Ivy Home Page`_ in addition to our tutorial.
Within the documentation of
this python package we suppose that you are already familiar with the way an
ivy bus works, and with how the corresponding framework is organized.

:py:mod:`ivy.std_api`
~~~~~~~~~~~~~~~~~~~~~
Once familiar with the ivy framework, you'll find in the `std_api` module the
exact API you're expecting (see for example the  `The Ivy C library`_).

An example of use, directly taken from the original swig-base python release,
is included with the package, see ``examples/pyhello.py``.

.. important:: One big difference with the original implementation is that
   there is nothing like a "main loop": the server is activated as soon as the
   method :py:func:`ivy.std_api.IvyStart` is called, and the
   :py:func:`ivy.std_api.IvyMainLoop` method simply waits for the server to
   terminate (the server runs in a separate thread).

:py:mod:`ivy.ivy`
~~~~~~~~~~~~~~~~~

It's where the logic is implemented: the module `std_api` is built on top of it.

This package allows to manage more than one ivy bus in an application.
Refer to the implementation of the `ivy` module for an example of how to use it.

Logging
-------

  The module issues messages through python's standard ``logging`` module:

    - logger's name: ``'Ivy'``
    - default level: ``logging.INFO``
    - default handler: a ``logging.StreamHandler`` logging messages to the
      standard error stream.

  For example, if you need to see all messages issued by the package, including
  debug messages, use the following code excerpt:

  .. code:: python

    import logging
    logging.getLogger('Ivy').setLevel(logging.DEBUG)

  Further details can be found in the `Python standard documentation
  <http://docs.python.org/lib/module-logging.html>`_.


Supported python
----------------

Python 3.7 or higher is needed.

.. note:: ivy-python v3.3 was the last one supporting Python 2.7.

Misc. notes
-----------

  - direct msg: to app_name == the last one registered w/ that name (for
    example register ivyprobe 3 times and send a direct msg to IVYPROBE from
    one of them)

  - regexps order and ids: ivyprobe e.g. subscribes regexp in reverse order of
    ids.  For each match, send the appropriate message.
    documented.


License
-------

This software is distributed under the `"new" BSD license
<http://www.opensource.org/licenses/bsd-license.php>`_,

(please refer the file ``LICENSE`` for full legal details)

Copyright (c) 2005-2023 Sebastien Bigaret <sebastien.bigaret@telecom-bretagne.eu>

.. _Ivy Home Page: http://www.eei.cena.fr/products/ivy/
.. _The Ivy C library: http://www.eei.cena.fr/products/ivy/documentation/ivy-c.pdf
.. _Ivy downloads page: http://www.eei.cena.fr/products/ivy/download/binaries.html
"""
__version__ = '4.0'
