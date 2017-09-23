#The point of this script is to automatically launch the script at boot. 
#Run this script by using crontab and the @reboot command.
#For example: crontab -u pi -e will open the pi user's startup.
# Scroll to the bottom and specify the full location of this script.
# For Example: @reboot /home/pi/sign_launcher.sh
# should be placed at the bottom of the crontab.

sleep 30
screen -dmS sign sudo python /home/pi/python.py
