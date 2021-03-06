Dance event registration and ticketing app.

.. image:: https://travis-ci.org/littleweaver/django-brambling.svg?branch=master
    :target: https://travis-ci.org/littleweaver/django-brambling

Naming
======

The name of this software is django-brambling. The name for use within the content of the application and for marketing purposes is Dancerfly.

Development
=============

Prerequisites
-------------

The installation instructions below assume you have the following software on your machine:

* `Python 2.7.x <http://www.python.org/download/releases/2.7.6/>`_
* `Pip <https://pip.readthedocs.org/en/latest/installing.html>`_
* `virtualenv <https://virtualenv.pypa.io/en/stable/installation/>`_ (optional)
* `virtualenvwrapper <http://virtualenvwrapper.readthedocs.org/en/latest/install.html>`_ (optional)

Installation instructions
-------------------------

If you are using virtualenv or virtualenvwrapper, create and activate an environment. E.g.,

.. code:: bash

    mkvirtualenv brambling # Using virtualenvwrapper.

Then, to install:

.. code:: bash

    # Clone django-brambling to a location of your choice.
    git clone https://github.com/littleweaver/django-brambling.git

    # Install django-brambling.
    pip install --no-deps -e django-brambling

    # Install python requirements. This may take a while.
    pip install -r django-brambling/test_project/requirements.txt


Get it running
--------------

.. code:: bash

    cd django-brambling/test_project
    python manage.py syncdb    # Create/sync the database.
    python manage.py runserver # Run the server!

Then, navigate to ``http://127.0.0.1:8000/`` in your favorite web browser!


.. image:: https://badges.gitter.im/Join%20Chat.svg
   :alt: Join the chat at https://gitter.im/littleweaver/django-brambling
   :target: https://gitter.im/littleweaver/django-brambling?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge


Deploying to a server
---------------------

First, set up an ubuntu server on whatever service and set up your ssh config
appropriately. Once that's done, install fabric (if you don't have it already): `pip install fabric`

Then, all you need to do is run `fab -H name-of-server deploy:branch-name`. This does the following:

* Installs our server configuration tool, `salt <http://saltstack.com/>`_, which will handle most
  of the heavy lifting for you. This only happens if salt isn't installed yet.
* Syncs your local pillar data with the remote version using rsync.
* Deploys the specified branch from Github.
* Runs salt.
* Runs migrations.
* Collects static files.

Each of these steps can also be run individually. Run `fab` with no arguments to see a full list of commands, or
check out fabfile.py.
