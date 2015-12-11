import json

from twisted.web import http

from werkzeug.exceptions import NotFound

from txplaya.player import MainController
from txplaya.routes import url_map


_match = url_map.bind('').match

_NOT_FOUND_MSG = json.dumps({'msg': 'Not found!'})

def getFrontHandler():

    _mainController = MainController()

    class FrontHandler(http.Request):

        mainController = _mainController

        def process(self):
            try:
                controllerClass, kwargs = _match(self.path, method = self.method)

            except NotFound:
                self.setHeader('Content-Type', 'text/html')
                self.setResponseCode(http.NOT_FOUND)
                self.write(_NOT_FOUND_MSG)
                self.finish()
                return

            controllerClass(self, **kwargs)

    return FrontHandler


class FrontChannel(http.HTTPChannel):
    requestFactory = getFrontHandler()


class HttpFactory(http.HTTPFactory):
    protocol = FrontChannel
