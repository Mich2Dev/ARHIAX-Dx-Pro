#!/bin/bash
PG_BIN=$(find /usr/lib/postgresql -name postgres -type f -executable | head -n 1)
PG_DATA=$(find /var/lib/postgresql -name main -type d | head -n 1)
PG_CONF=$(find /etc/postgresql -name postgresql.conf -type f | head -n 1)
exec $PG_BIN -D $PG_DATA -c config_file=$PG_CONF
