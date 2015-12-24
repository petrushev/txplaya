from PyQt5.QtCore import QSettings


settings = QSettings('TxPlaya')


def host():
    return settings.value('host', 'localhost')

def port():
    return settings.value('port', 8070, type=int)

def baseUrl():
    return 'http://%s:%d' % (host(), port())

def setHost(host):
    settings.setValue('host', host)

def setPort(port):
    settings.setValue('port', port)
