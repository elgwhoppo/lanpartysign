#!/bin/bash

screen_session_name="SIGN"
command_to_run="python /home/pi/lanpartysign/sign.py"

while true; do
    sleep 5
    if screen -list | grep -q "$screen_session_name"; then
        echo "The screen session '$screen_session_name' is running."
    else
        echo "The screen session '$screen_session_name' is not running. Starting it..."
        screen -S "$screen_session_name" -d -m $command_to_run
    fi
done
