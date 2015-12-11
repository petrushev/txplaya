from werkzeug.routing import Rule, Map

from txplaya import controllers

url_map = Map([
    Rule('/stream',
         endpoint=controllers.Stream),
    Rule('/playlist', defaults={'action': 'getData'},
         endpoint=controllers.PlaylistManager),
    Rule('/playlist/insert/<int:position>/<path:filepath>', defaults={'action': 'insert'},
         endpoint=controllers.PlaylistManager),
    Rule('/playlist/insert/<path:filepath>', defaults={'action': 'insert'},
         endpoint=controllers.PlaylistManager),
    Rule('/playlist/remove/<int:position>', defaults={'action': 'remove'},
         endpoint=controllers.PlaylistManager),
    Rule('/playlist/move/<int:start>/<int:end>', defaults={'action': 'move'},
         endpoint=controllers.PlaylistManager),
    Rule('/playlist/clear', defaults={'action': 'clear'},
         endpoint=controllers.PlaylistManager),
    Rule('/playlist/current', defaults={'action': 'current'},
         endpoint=controllers.PlaylistManager),
    Rule('/player/start/<int:position>', defaults={'action': 'start'},
         endpoint=controllers.Player),
    Rule('/player/start', defaults={'action': 'start'},
         endpoint=controllers.Player),
    Rule('/player/stop', defaults={'action': 'stop'},
         endpoint=controllers.Player),
    Rule('/player/pause', defaults={'action': 'pause'},
         endpoint=controllers.Player),
])
