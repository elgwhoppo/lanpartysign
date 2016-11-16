#!/bin/sh
#grabs the ping of a server and outs it to a file
#place in 

while : 
do
  ping -c 1 chorus.co.nz | grep round-trip | cut -c 33-37 > /usr/local/www/pingnow.txt
  sleep 1
done
