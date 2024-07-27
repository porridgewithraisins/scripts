#! /usr/bin/env bash

# this is just a note no use running it
#
# But do clang -MJ whatever.o.json
# and then run `sed -e '1s/^/[\n/' -e '$s/,$/\n]/' *.o.json > compile_commands.json`
