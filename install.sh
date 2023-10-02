#use this script to install the required packages for the project

#Install the required packages
#Install Raspbian. At time of writing, this was used: 

#pi@speedsign:~ $ cat /etc/os-release
#PRETTY_NAME="Raspbian GNU/Linux 11 (bullseye)"
#NAME="Raspbian GNU/Linux"
#VERSION_ID="11"
#VERSION="11 (bullseye)"
#VERSION_CODENAME=bullseye
#ID=raspbian
#ID_LIKE=debian
#HOME_URL="http://www.raspbian.org/"
#SUPPORT_URL="http://www.raspbian.org/RaspbianForums"
#BUG_REPORT_URL="http://www.raspbian.org/RaspbianBugs"

pip3 install pysnmp
#had to downgrade due to compatibility issue 
pip3 install pyasn1==0.4.8

git clone https://github.com/elgwhoppo/lanpartysign.git