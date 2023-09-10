#!/bin/bash

screen_session_name="SNMP"
command_to_run="python /home/pi/speedsign/snmp.py"

screen_session_name1="SIGN"
command_to_run1="sudo python /home/pi/speedsign/python.py"

while true; do
    sleep 3
    if screen -list | grep -q "$screen_session_name"; then
        echo "The screen session '$screen_session_name' is running."
    else
        echo "The screen session '$screen_session_name' is not running. Starting it..."
        screen -S "$screen_session_name" -d -m $command_to_run
    fi
    sleep 3 
    if screen -list | grep -q "$screen_session_name1"; then
        echo "The screen session '$screen_session_name1' is running."
    else
        echo "The screen session '$screen_session_name1' is not running. Starting it..."
        screen -S "$screen_session_name1" -d -m $command_to_run1
    fi

done
#screen -S SNMP -d -m sudo python /home/pi/speedsign/snmp.py
#screen -S SIGN -d -m sudo python /home/pi/speedsign/python.py
