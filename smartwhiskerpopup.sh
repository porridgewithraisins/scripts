#! /usr/bin/env bash

mkdir -p ~/.local/share/smartwhiskerpopup
exec > >(tee ~/.local/share/smartwhiskerpopup/script.log) 2>&1

{ read -r id1; read -r id2; } < <(xfce4-popup-whiskermenu -l)

eval "$(xdotool getmouselocation --shell)"

monitor=$(
    xrandr |
    awk -v mx="$X" '
    / connected( primary)? [0-9]+x[0-9]+\+/ {
        match($0, /([0-9]+)x([0-9]+)\+([0-9]+)\+([0-9]+)/, a)

        left  = a[3]
        right = a[3] + a[1]

        if (mx >= left && mx < right) {
            print $1
            exit
        }
    }'
)

case "$monitor" in
    eDP)
        xfce4-popup-whiskermenu -i "$id1"
        ;;
    DisplayPort-0)
        xfce4-popup-whiskermenu -i "$id2"
        ;;
esac
