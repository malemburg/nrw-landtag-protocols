NRW Landtag Protocols
=====================

Parse NRW Landtag plenary session protocols into JSON files.

This is a project I worked on during the Python Meeting Düsseldorf Herbst
Sprint 2021, together with Oliver Stapel.

Loading data
------------

```
# Load all available documents for a period
./load_data.py <period>
# Load a specific document
./load_data.py <period> <index>
```

The loader is smart enough to only load documents which have not yet
been loaded. The load status is stored in JSON file in the protocols/
folder.

Parsing data
------------

```
# Parse all available documents for a period
./parse_data.py <period>
# Parse a specific document
./parse_data.py <period> <index>
```

The parser will create a new JSON file for each HTML file it finds.

It currently supports periods 14 - 17.

OpenSearch using Docker
-----------------------

To start a local OpenSearch cluster for experiments, run
`make start-os`. To stop the cluser, run `make stop-os`.

Be sure that you have set vm.max_map_count=262144 in your /etc/sysctl.conf
and then run `sudo sysctl -p` to have the values loaded,
or run `sudo sysctl -w vm.max_map_count=262144` to dynamically set the
value. OpenSearch won't start without this setting.

Once started, you can point your browser to localhost:5601 and log in
using the default credentials admin:admin. After login, change the password
to something strong to protect the instance.

In order to run snapshots, you have to register the snapshot repo
under os-data/snapshots. This is done using the OS console and the
command:
```
PUT _snapshot/os-snapshots
{
  "type": "fs",
  "settings": {
    "location": "/mnt/snapshots"
  }
}
```

Once this is in place, snapshots can be created using, e.g.
```
PUT _snapshot/os-snapshots/2023-01-31
```

---
Marc-Andre Lemburg, Nov 2021 - Jan 2023
