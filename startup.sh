#!/bin/bash

#!/bin/bash

# Function to check if the network is ready
check_network() {
    while ! ping -c 1 google.com &> /dev/null; do
        echo "Network is not ready. Waiting..."
        sleep 5
    done
    echo "Network is now ready."
}

# Call the check_network function to wait for the network
check_network

# Continue with your script here
echo "Network is ready. Continuing with the script."

# do the thing
#screen -S SNMP -d -m python /home/pi/speedsign/snmp.py
#sleep 15
#screen -S SIGN -d -m sudo python /home/pi/speedsign/python.py
#sleep 15
#screen -S SIGN -d -m python /home/pi/lanpartysign/sign.py
sleep 15
screen -S WDOG -d -m /home/pi/lanpartysign/watchdog.sh