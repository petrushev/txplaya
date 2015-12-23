from os import environ

from twisted.application.service import Application
from twisted.application.internet import TCPServer

from txplaya.http import HttpFactory

BIND_ADDRESS = environ.get('TXPLAYA_BIND_ADDRESS', 'localhost')
PORT = int(environ.get('TXPLAYA_PORT', 8070))

httpFactory = HttpFactory()

application = Application('Playa')
TCPServer(PORT, httpFactory, interface=BIND_ADDRESS).setServiceParent(application)
