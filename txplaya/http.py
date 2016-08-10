import json

from twisted.web.http import Request, HTTPChannel, HTTPFactory, NOT_FOUND
from twisted.application.internet import TCPServer as BaseTCPServer

from werkzeug.exceptions import NotFound

from txplaya.player import MainController
from txplaya.routes import url_map


_match = url_map.bind('').match

_NOT_FOUND_MSG = json.dumps({'msg': 'Not found!'}).encode('utf-8')

def getFrontHandler():

    _mainController = MainController()

    class FrontHandler(Request):

        mainController = _mainController

        def process(self):
            try:
                controllerClass, kwargs = _match(self.path, method = self.method)

            except NotFound:
                self.setHeader('Content-Type', 'application/json')
                self.setResponseCode(NOT_FOUND)
                self.write(_NOT_FOUND_MSG)
                self.finish()
                return

            controllerClass(self, **kwargs)

    return FrontHandler


class FrontChannel(HTTPChannel):
    requestFactory = getFrontHandler()


httpFactory = HTTPFactory.forProtocol(FrontChannel)


class TCPServer(BaseTCPServer):

    def startService(self):
        BaseTCPServer.startService(self)

        protocolFactory = self.args[1]
        mainController = protocolFactory.protocol.requestFactory.mainController
        mainController.onStart()

    def stopService(self):
        protocolFactory = self.args[1]
        mainController = protocolFactory.protocol.requestFactory.mainController
        mainController.onStop()

        BaseTCPServer.stopService(self)
