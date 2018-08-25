#The point of this script is to automatically launch the script at boot. 
#Run this script by using crontab and the @reboot command.
#For example: crontab -u pi -e will open the pi user's startup.
# Scroll to the bottom and specify the full location of this script.
# For Example: @reboot /home/pi/sign_launcher.sh
# should be placed at the bottom of the crontab.
# For added stability, reboot the pi every 6 hours or so, there are still weird crashes on the pi. 
# Sudo -i to switch to root and open crotab with crontab -e
# Add the following: 0 */6 * * * /sbin/reboot

sleep 30
screen -dmS sign sudo python /home/pi/python.py
