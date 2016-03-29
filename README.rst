todo.txt-pylib
==============

``todo.txt-pylib`` is a Python 3 library to parse, manipulate, query and render
tasks in the `todo.txt`_-format in a pythonic manner. It can easily be extended.


Installation
------------

::

    pip install todo.txt-pylib


Usage
-----

.. code:: python

    from todotxt import Task
    task = Task('do something')

There are more advanced examples in the `documentation`_.


Hacking
-------

`Clone the repo`_, setup and activate a `virtual envrionment`_, then

::

    ./setup.py develop
    pip install requirements-dev.txt
    ./run-tests


Resources
---------

-  `Documentation with examples and API`_
-  `Package at the warehouse`_


.. _todo.txt: https://todotxt.com
.. _documentation: http://todotxt-pylib.readthedocs.org/en/latest/
.. _Clone the repo: https://help.github.com/articles/fork-a-repo/
.. _virtual envrionment: https://github.com/berdario/pew
.. _Documentation with examples and API: http://todotxt-pylib.readthedocs.org/en/latest/
.. _Package at the warehouse: https://warehouse.python.org/project/todo.txt-pylib/
