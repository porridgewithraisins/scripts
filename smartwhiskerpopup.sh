#! /usr/bin/env bash

mkdir -p ~/.local/share/smartwhiskerpopup
exec > >(tee ~/.local/share/smartwhiskerpopup/script.log) 2>&1

{ read -r id1; read -r id2; } < <(xfce4-popup-whiskermenu -l)

eval "$(xdotool getmouselocation --shell)"

if test "$X" -le 1920; then
    xfce4-popup-whiskermenu -i "$id1";
else
    xfce4-popup-whiskermenu -i "$id2";
fi
