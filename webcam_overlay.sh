#!/usr/bin/env bash

v4l2-ctl --list-devices | grep -A1 --no-group-separator ':$' | cut -d'(' -f1 | paste -d'\t' - - | sed 's/\t\t/\t/' |
    grep "$(v4l2-ctl --list-devices | grep ':$' | cut -d'(' -f1 | xargs -d '\n' zenity --list --column='Cameras')" |
    cut -f2 | xargs ffplay -noborder -alwaysontop -x 426 -y 240
