txplaya
=======

Web based audio player build on Twisted


Requirements
------------

- Twisted
- requests
- PyQt5
- werkzeug
- mutagen


Running
-------

Build resource, ui and translation files:

.. code:: python

    ./build.sh

Start server with:

.. code:: python

    TXPLAYA_LIBPATH="/path/to/your/music" twistd -ny playaservice.py

Start client with:

.. code:: python

    python playagui.py

Open browser location: ``http://localhost:8070/stream``

You can add tracks by drag-n-droping files from a file manager.
