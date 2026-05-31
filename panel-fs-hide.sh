#! /usr/bin/env bash

set -euo pipefail

: "${PANEL_FS_HIDE_DEBUG:=0}"

test "$PANEL_FS_HIDE_DEBUG" = "2" && set -x

LOG=/tmp/panel-fs-hide.log

log() {
    test "$PANEL_FS_HIDE_DEBUG" = "0" && return 0
    echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"
}

handle_panels() {
    declare -A fullscreen_xs

    while read -r wid; do
        if xprop -id "$wid" _NET_WM_STATE 2>/dev/null | grep -q "FULLSCREEN"; then
            fs_x=$(xwininfo -id "$wid" | awk '/Absolute upper-left X/ {print $NF}')
            log "Fullscreen window $wid at x=$fs_x"
            fullscreen_xs[$fs_x]=1
        fi
    done < <(wmctrl -l | awk '{print $1}')

    while read -r panel_id; do
        panel_x=$(xwininfo -id "$panel_id" | awk '/Absolute upper-left X/ {print $NF}')
        if test -n "${fullscreen_xs[$panel_x]:-}"; then
            if ! xprop -id "$panel_id" _NET_WM_STATE | grep -q "BELOW"; then
                log "Panel $panel_id x=$panel_x -> add,below"
                wmctrl -i -r "$panel_id" -b add,below
            fi
        else
            if xprop -id "$panel_id" _NET_WM_STATE | grep -q "BELOW"; then
                log "Panel $panel_id x=$panel_x -> remove,below"
                wmctrl -i -r "$panel_id" -b remove,below
            fi
        fi
    done < <(wmctrl -l | awk '/xfce4-panel/ {print $1}')
}

log "Starting"

handle_panels

while true; do
    xprop -spy -root _NET_ACTIVE_WINDOW | while read -r line; do
        log "Active window changed: $line"
        handle_panels
    done
done &

while true; do
    xprop -spy -root _NET_CLIENT_LIST_STACKING | while read -r line; do
        log "Stacking changed: $line"
        handle_panels
    done
done &

wait
