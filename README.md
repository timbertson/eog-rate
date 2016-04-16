eog-rate
--------

<img src="http://gfxmonk.net/dist/status/project/eog-rate.png">

A simple rating system for the Eye Of Gnome image viewer. You can set star ratings (between 0-3), and tags (comma-separated).

This data is stored both as `xattr` metadata on each file for interoperability / convenience / locality, and as a plain JSON file (one per directory) for resilience against backup or transport systems that don't preserve `xattr` metadata. Read up on [dumbattr](http://gfxmonk.net/dist/0install/python-dumbattr.xml) for the technical details (including a command to bulk-restore xattrs from the JSON serialization after such an event).

eog-rate comes with a command-line tool which can be used to find files (recursively) with ratings or tags that satisfy specific criteria. But you can use the `dumbattr` library (or xattr / JSON directly) to do whatever you want - it's your data.
