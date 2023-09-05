#!/bin/bash
sleep 15
screen -S SNMP -d -m sudo python /home/pi/speedsign/snmp.py
screen -S SIGN -d -m sudo python /home/pi/speedsign/python.py
