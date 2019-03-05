# !! THIS FILE HAS BEEN DEPRECATED IN LIU OF PYTHON.PY 1.3 !!
#
#!/bin/sh
# Written by Joe Clarke
# This script is to be run on the pfSense box itself and it depends on vnstat being installed. 
# Change the interface called on the vnstat line to whatever interface you'd like to track bandwidth on, LAN is best for multi-wan configs. 
# This script totals the tx and rx traffic together for the aggregate, but it can be modified if only download is of interest. 
#
# On pfSense this shell script can be placed in the /usr/local/etc/rc.d/ directory for automatic start
# make sure to run chmod +x grabbw.sh so that it can be executed and it will run at start automatically on boot. 
#
# Initially we did the interpolation here, but it turned out that files outed into /usr/local/www/ are only updated by pfsense around once per second. 
# So we opted to do the interpolation in python on the raspberry pi. 
#
# To run the script from console, copy to /tmp and run /bin/sh /tmp/grabbw.sh
#
# To test if it's working, navigate to <yourpfsenseIP>/bwnow.txt and you should see the value in bps. 
#
# 1.0 Initial Release
# 1.1 Added second interface

while :
do

rxratescaled=""
txratescaled=""
rxbps=""
txbps=""
totalbps=""
totalbpsbce0=""
totalmbpsbce0=""
totalbpsbce2=""
totalmbpsbce2=""

vnstat -i bce0 -tr 2 > /tmp/output.log
rxratescaled=$(tail /tmp/output.log | grep "rx" | cut -c 15-29)

#Clean up rx, boil down to bps
echo $rxratescaled > /tmp/output-temp-rx.log
if grep -q "Mbit" /tmp/output-temp-rx.log; then
        #Trim off Mbit/s
        rxbps=$(tail /tmp/output-temp-rx.log | tr -d 'Mbit/s')
        echo $rxbps > /tmp/output-temp-rx.log
        rxbps=$(tail /tmp/output-temp-rx.log | tr -d ' ')
        #Convert Mbit to bit
        if grep -q . /tmp/output-temp-rx.log; then
                # We assume when there's a . that there are two numbers following it. As a result add four 0s to convert.
                # We also assume that every time Mbit/s is used there's a decmial followed by 2 numbers.
                rxbps=$(tail /tmp/output-temp-rx.log | tr -d '.')
                rxbps=$rxbps"0000"
        fi
        echo "converted rxbps: ${rxbps}"
elif grep -q "kbit" /tmp/output-temp-rx.log; then
        #Trim off Kbit/s
        rxbps=$(tail /tmp/output-temp-rx.log | tr -d 'kbit/s')
        #Convert Kbit to bit
        rxbps=$((${rxbps}*1000))
        #echo "converted rxbps: ${rxbps}"
fi

txratescaled=$(tail /tmp/output.log | grep "tx" | cut -c 15-29)

#Clean up TX, boil down to bps
echo $txratescaled > /tmp/output-temp-tx.log
if grep -q "Mbit" /tmp/output-temp-tx.log; then
        #Trim off Mbit/s
        txbps=$(tail /tmp/output-temp-tx.log | tr -d 'Mbit/s')
        echo $txbps > /tmp/output-temp-tx.log
        txbps=$(tail /tmp/output-temp-tx.log | tr -d ' ')
        #Convert Mbit to bit
        if grep -q . /tmp/output-temp-tx.log; then
                # We assume when there's a . that there are two numbers following it. As a result add four 0s to convert.
                # We also assume that every time Mbit/s is used there's a decmial.
                txbps=$(tail /tmp/output-temp-tx.log | tr -d '.')
                txbps=$txbps"0000"
        fi
        echo "converted txbps: ${txbps}"
elif grep -q "kbit" /tmp/output-temp-tx.log; then
        #Trim off Kbit/s
        txbps=$(tail /tmp/output-temp-tx.log | tr -d 'kbit/s')
        #Convert Kbit to bit
        txbps=$((${txbps}*1000))
        #echo "converted txbps: ${txbps}"
fi

totalbpsbce0=`expr $txbps + $rxbps`
echo "total  bps bce0: ${totalbpsbce0}"
totalmbpsbce0=`expr $totalbpsbce0 / 1000000`
echo "total mbps bce0: ${totalmbpsbce0}"


#Start second inteface bce2
vnstat -i bce2 -tr 2 > /tmp/output.log
rxratescaled=$(tail /tmp/output.log | grep "rx" | cut -c 15-29)

#Clean up rx, boil down to bps
echo $rxratescaled > /tmp/output-temp-rx.log
if grep -q "Mbit" /tmp/output-temp-rx.log; then
        #Trim off Mbit/s
        rxbps=$(tail /tmp/output-temp-rx.log | tr -d 'Mbit/s')
        echo $rxbps > /tmp/output-temp-rx.log
        rxbps=$(tail /tmp/output-temp-rx.log | tr -d ' ')
        #Convert Mbit to bit
        if grep -q . /tmp/output-temp-rx.log; then
                # We assume when there's a . that there are two numbers following it. As a result add four 0s to convert.
                # We also assume that every time Mbit/s is used there's a decmial followed by 2 numbers.
                rxbps=$(tail /tmp/output-temp-rx.log | tr -d '.')
                rxbps=$rxbps"0000"
        fi
        echo "converted rxbps: ${rxbps}"
elif grep -q "kbit" /tmp/output-temp-rx.log; then
        #Trim off Kbit/s
        rxbps=$(tail /tmp/output-temp-rx.log | tr -d 'kbit/s')
        #Convert Kbit to bit
        rxbps=$((${rxbps}*1000))
        #echo "converted rxbps: ${rxbps}"
fi

txratescaled=$(tail /tmp/output.log | grep "tx" | cut -c 15-29)

#Clean up TX, boil down to bps
echo $txratescaled > /tmp/output-temp-tx.log
if grep -q "Mbit" /tmp/output-temp-tx.log; then
        #Trim off Mbit/s
        txbps=$(tail /tmp/output-temp-tx.log | tr -d 'Mbit/s')
        echo $txbps > /tmp/output-temp-tx.log
        txbps=$(tail /tmp/output-temp-tx.log | tr -d ' ')
        #Convert Mbit to bit
        if grep -q . /tmp/output-temp-tx.log; then
                # We assume when there's a . that there are two numbers following it. As a result add four 0s to convert.
                # We also assume that every time Mbit/s is used there's a decmial.
                txbps=$(tail /tmp/output-temp-tx.log | tr -d '.')
                txbps=$txbps"0000"
        fi
        echo "converted txbps: ${txbps}"
elif grep -q "kbit" /tmp/output-temp-tx.log; then
        #Trim off Kbit/s
        txbps=$(tail /tmp/output-temp-tx.log | tr -d 'kbit/s')
        #Convert Kbit to bit
        txbps=$((${txbps}*1000))
        #echo "converted txbps: ${txbps}"
fi

totalbpsbce2=`expr $txbps + $rxbps`
echo "total  bps bce2: ${totalbpsbce2}"
totalmbpsbce2=`expr $totalbpsbce2 / 1000000`
echo "total mbps bce2: ${totalmbpsbce2}"
echo ""
totalbps=`expr $totalbpsbce0 + $totalbpsbce2`
echo "total bps combined: ${totalbps}"


echo $totalbps > /usr/local/www/bwnow.txt

done

