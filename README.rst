Dask-Mesos
==========

|Build Status|

.. |Build Status| image:: https://travis-ci.org/dask/dask-mesos.svg
   :target: https://travis-ci.org/dask/dask-mesos

A simple Mesos Scheduler to deploy Dask.distributed workers.

Example
-------

Set up Tornado IOLoop in a background thread

.. code-block:: python

   >>> from tornado.ioloop import IOLoop
   >>> from threading import Thread
   >>> loop = IOLoop()
   >>> thread = Thread(target=loop.start)
   >>> thread.daemon = True
   >>> thread.start()

Start Dask Scheduler with that thread

.. code-block:: python

   >>> from distributed import Scheduler
   >>> dask_scheduler = Scheduler(loop=loop)
   >>> loop.add_callback(dask_scheduler.start)

Start Mesos Scheduler with that scheduler

.. code-block:: python

   >>> from dask_mesos import FixedScheduler
   >>> mesos_scheduler = FixedScheduler(dask_scheduler, target=10, cpus=2,
   ...                                  mem=8192, executable='dask-worker')
   >>> mesos_scheduler.start()

Mesos launches workers that connect up to our local scheduler

.. code-block:: python

   >>> dask_scheduler
   <Scheduler: 192.168.0.1, processes: 10, cores: 20>

Test locally
------------

This sets up a docker cluster of one Mesos master and two Mesos slaves using
docker-compose.

**Requires**:

- docker version >= 1.11.1
- docker-compose version >= 1.7.1

::

   export DOCKER_IP=127.0.0.1
   docker-compose up

With the Mesos docker setup operational, move *into* the ``mesos_master``
docker container and run py.test

::

    docker exec -it mesos_master /bin/bash
    cd dask-mesos
    py.test dask_mesos

This directory, ``dask-mesos`` is an attached volume in the ``mesos_master``.


Additional notes
----------------

- Master and Slaves have dask.distributed installed its github repository
- Mesos container names:
  - mesos_master
  - mesos_slave_one
  - mesos_slave_two


Web UIs
-------

- http://localhost:5050/ for Mesos master UI
- http://localhost:5051/ for the first Mesos slave UI
- http://localhost:5052/ for the second Mesos slave UI
- http://localhost:8080/ for Marathon UI
- http://localhost:8888/ for Chronos UI


History
-------

Mesos Docker-compose solution originally forked from https://github.com/bobrik/mesos-compose
