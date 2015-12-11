from twisted.application.service import Application
from twisted.application.internet import TCPServer

from txplaya.http import HttpFactory

httpFactory = HttpFactory()

application = Application('Playa')
TCPServer(8070, httpFactory).setServiceParent(application)
