#! /usr/bin/env bash

function generateImage {
    if [[ $1 == "full" ]]; then
        import -silent -window root png:-
    elif [[ $1 == "mouse" ]]; then
        import -silent -window `xdotool getmouselocation | cut -d' ' -f4 | cut -d: -f2` png:- 
    elif [[ $1 == "active" ]]; then
        import -silent -window `xdotool getactivewindow` png:-
    else # region selection
        import -silent png:-
    fi
}

generateImage $1 | xclip -selection clipboard -t image/png