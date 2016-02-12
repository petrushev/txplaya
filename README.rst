txplaya
=======

Web based audio player build on Twisted


Requirements
------------

  * Server

    - Twisted
    - werkzeug
    - mutagen
    - pylast

  * Qt client

    - PyQt5
    - werkzeug
    - unidecode


Running server
--------------

Environment variables:

  - TXPLAYA_LIBPATH - path to music library, multiple paths supported. default: ~/Music
  - TXPLAYA_BIND_ADDRESS - http address, default: localhost
  - TXPLAYA_PORT - http port, default: 8070

Optional:

  - TXPLAYA_LASTFM_USER - lastfm credentials
  - TXPLAYA_LASTFM_PASS
  - TXPLAYA_LASTFM_KEY
  - TXPLAYA_LASTFM_SECRET


Start:

.. code:: python

    twistd -ny playaservice.py


Running GUI:
------------

Build resource, ui and translation files:

.. code:: python

    ./build.sh

Start:

.. code:: python

    python playagui.py

Open browser location: ``http://localhost:8070/stream``

You can add tracks by drag-n-droping files from a file manager.
