echo 'Building ui files...'
pyrcc5 -o txplayagui/ui/resource_rc.py txplayagui/ui/resource.qrc
pyuic5 -o txplayagui/ui/main.py txplayagui/ui/main.ui
pyuic5 -o txplayagui/ui/library.py txplayagui/ui/library.ui
pyuic5 -o txplayagui/ui/playlists.py txplayagui/ui/playlists.ui
pyuic5 -o txplayagui/ui/reconnectdialog.py txplayagui/ui/reconnectdialog.ui
pylupdate5 -verbose txplayagui/txplayagui.pro
lrelease -verbose txplayagui/txplayagui.pro
