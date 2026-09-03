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
sleep 15
screen -S WDOG -d -m /home/pi/lanpartysign/watchdog.sh
