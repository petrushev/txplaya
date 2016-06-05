from os import environ

from twisted.application.service import Application

from txplaya.http import TCPServer, httpFactory

BIND_ADDRESS = environ.get('TXPLAYA_BIND_ADDRESS', 'localhost')
PORT = int(environ.get('TXPLAYA_PORT', 8070))

application = Application('Playa')
TCPServer(PORT, httpFactory, interface=BIND_ADDRESS).setServiceParent(application)
