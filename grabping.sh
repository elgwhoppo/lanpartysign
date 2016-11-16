#!/bin/sh
# grabs the ping of a server and outs it to a file
# on pfSense this shell script can be placed in the /usr/local/etc/rc.d/ directory for automatic start
# make sure to run chmod +x grabbw.sh so that it can be executed. 
# recommended minmum delay of 1s to ensure ping completes

while : 
do
  ping -c 1 chorus.co.nz | grep round-trip | cut -c 33-37 > /usr/local/www/pingnow.txt
  sleep 1
done
