Here it is in action!
https://raw.githubusercontent.com/elgwhoppo/LANPartySign/master/images/xIRKag8QQ-qkcFby.mp4

Hardware
========
Raspberry Pi
------------
We used a Raspberry Pi 3, but any Raspberry Pi with at least 14 available GPIO
pins should do.

Aluminum street sign
--------------------
http://www.roadtrafficsigns.com/Custom-Metal-Sign/Custom-Metal-Sign-24x18/SKU-K-3409-BK.aspx

The text used to create “YOUR SPEED” with sufficient space:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
YOUR
SPEED
 
 
 
 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Press [Enter] four times after “SPEED” to create some space.

LED panels
----------
![LED panels JB Welded together](https://github.com/elgwhoppo/LANPartySign/blob/master/images/panels-jbwelded.jpg)

Six 4” common anode LED panels, three in red, and three in green were glued together using JB Weld.  It’s not very pretty on the back, but no one sees the rear of the panels anyway.  I used a wet paper towel to wipe up the excess that oozed out the front.

These are the panels we used:

http://www.ebay.com/itm/182018966801

http://www.ebay.com/itm/252168875198

Power supply
------------
A 12V/2A power adapter is sufficient to provide power to the RPi and drive the LED’s. This isn’t terribly special. This is the same type of wallwart-style power supply that comes with routers and cable modems.

https://www.amazon.com/gp/product/B0194B7WSI/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1

The Raspberry Pi is also draws from the same power adapter via a cheap step-down
buck converter. This is the one we used.

https://www.amazon.com/gp/product/B008BHB4L8/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1

LED driver board
----------------
![Schematic](https://github.com/elgwhoppo/LANPartySign/blob/master/schematic.png)
![Schematic](https://github.com/elgwhoppo/LANPartySign/blob/master/schem2.png)

### Source IC
A UDN2984A source driver is required as the RPi’s GPIO outputs neither source enough voltage (3.3V max) or current (\~30mA total) to drive the large LED panels.

### Sink IC
A ULN2003AN Darlington array is required as the RPi’s GPIO can’t sink the return current without emitting smoke. A 2N7000 FET is used to drive one of the cathodes because the Darlington array I selected only had 7 pins and I needed 8.

### Resistors
Current limiting resistors are required to keep the LED panels from burning up, and to keep the brightness between the two types of panels uniform. The segments that form each digit require different values from the decimal point as the decimal point has less LED’s inside.

The green segments used 110ohm resistors and red segments used 150ohm resistors.  The green decimal point used a 4000ohm resistor and the red decimal point used a 800ohm resistor.

You may change the resistor values to your liking if you’d like it brighter or darker. We chose higher values since the sign would be used in a dimly-lit room (i.e. a LAN party). For a brighter sign, use a lower value. I wouldn’t suggest going lower than 60ohm for the digits and 250ohm for the decimal point.

### Connections to the Raspberry Pi
Six GPIO’s (GPIO4, 17, 18, 27, 22, and 26) are used to bring the input side of the source driver high, which allows 12V to flow out the output side into the anode of each LED panel, which activates a digit.

Eight GPIO’s (GPIO24, 22, 29, 31, 32, 33, 35, 36) are used to bring the input side of the Darlington array high which grounds out the appropriate cathode. This activates a segment (or the decimal point).

Pins 2 and 4 power the Raspberry Pi through the step-down buck converter.

### Wiring and connectors
A small length of 18GA wiring and barrel connectors are used to connect the LED driver board to the power supply.

https://www.amazon.com/gp/product/B0154MAECC/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1

https://www.amazon.com/gp/product/B01G6EAY0E/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1

The LED panels used CAT5e cabling with RJ45 crimped on the ends. They were connected to RJ45 jacks and breakout boards from Sparkfun. Three were used in total. One for the anode bus, one for the green cathode bus, and one for the red cathode bus. We could’ve consolidated the cathode buses, but I was afraid I wouldn’t have room for current limiting resistors behind the panels. The current limiting resistors are on the same board with the IC’s which required two individual CAT5e cathode busses.

https://www.sparkfun.com/products/643

https://www.sparkfun.com/products/716

A 40-pin IDE cable was sacrificed to make the connection between the LED driver board and the Raspberry Pi. 

Some protoboard was used to make soldering each panel to the bus easier, but I probably could’ve done with out them.

https://www.amazon.com/gp/product/B019Q14GRQ/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1

### Enclosures
The Raspberry Pi is housed in a ABS plastic case that allowed access to the
40-pin connector.

https://www.amazon.com/gp/product/B00MQWQT0A/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1

The LED driver board, due to the strange size of the protoboard I used is housed
in a 7.5” x 4.3” Hammond case.

https://www.amazon.com/gp/product/B0002BSRIO/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1

Fit and finish
==============
![LED driver in enclosure](https://github.com/elgwhoppo/LANPartySign/blob/master/images/led-driver-in-enclosure.jpg)
![Front of sign](https://github.com/elgwhoppo/LANPartySign/blob/master/images/front-of-sign.jpg)

A piece of tinted acrylic was glued to the front of the LED panels to give it a nice slick look.  Unfortunately it's very reflective and impossible to photograph without seeing a reflection of someone or something :(

https://www.amazon.com/gp/product/B01A1C16TK/ref=oh\_aui\_detailpage\_o02\_s00?ie=UTF8&psc=1

The Mb/s and ms units were printed on my laser printer using the same font used by the US Federal Highway Administration (Highway Gothic), laminated, and taped to the front of the sign because I ran out of time. However, more permanent unit labels printed on a vinyl printer will replace them.

https://github.com/elgwhoppo/LANPartySign/blob/master/units.eps

Four pairs of rare earth magnets keep the LED panel secured to the sign. Four magnets are adhered to the set of LED panels with JB Weld. I love JB Weld.

The enclosure for the Raspberry Pi and LED driver board are double-sided-taped to the back of the aluminum sign.

Software
========
We used on rebuild: 
-   Raspberry Pi OS (32-bit)
-   Python 3.9.2 that came with updated Rasberry Pi OS
-   Screen for the watchdog process - sudo apt install screen 
-   https://pypi.org/project/pysnmp/ - sudo pip3 install pysnmp
-   pip3 install pyasn1==0.4.8 (had to downgrade for compatability)
-   The RPi.GPIO library. No install required with python 3.9.2. 

The Python Script
=================
The Python script does all the heavy lifting of the sign and runs on the Raspberry Pi. It creates the precisely-timed pulses required for multiplexing the digits, as well as gathering the data displayed on the sign.

The speed at which values are fetched by adjusting “fetchrate”, and the sign’s refresh rate can be adjusted using the “pulsewidth” value. A small amount of number crunching is done to create how long a segment or digit should stay on or off for the multiplexing.

The rest of the Python script is heavily derived from Rototron’s terrific 7 Segment LED tutorial. I would suggest viewing that as it’s a great explanation of using PWM to multiplex LED’s.

http://www.rototron.info/7-segment-led-tutorial-for-raspberry-pi/

It’s important to note that once a pulse is created (via PWM.add\_channel\_pulse), that GPIO pin will continue to pulse until instructed otherwise (i.e. overwritten by another use of PWM.add\_channel\_pulse, or killed via PWM.clear\_channel)

The http daemon only updates a file once per second even though the shell script is updating it quicker. To create the illustion it’s updating faster, a small section for “fuzzing” averages the previous two values to fabricate a new one.

Some error checking and exception handling is done to prevent the Python script from stopping if a ping times out, or a blank value is fetched from pfSense.

The Shell Script
================
This shell script runs on our pfSense unit, and using vnstat, outputs a value in bps accessible over HTTP by the Raspberry Pi. Hopefully elgwhoppo has more to say about it because he's the one that wrote it :)

tl;dr “what do i need to buy?”
==============================
Some of the parts may need to change based on your needs of the sign as well as if you don’t want to repeat the same poor design decisions I made.

### 1x Aluminum street sign
- http://www.roadtrafficsigns.com/Custom-Metal-Sign/Custom-Metal-Sign-24x18/SKU-K-3409-BK.aspx 

### 6x LED panels
- 3x http://www.ebay.com/itm/182018966801
- 3x http://www.ebay.com/itm/252168875198

### Power supplies
- 12V/2A power supply https://www.amazon.com/gp/product/B0194B7WSI/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1
- step-down buck converter https://www.amazon.com/gp/product/B008BHB4L8/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1

### LED driver board
- 1x large protoboard
- 6x small protoboard https://www.amazon.com/gp/product/B019Q14GRQ/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1
- 1x UDN2984A
- 1x 18-pin socket for UDN2984A
- 1x ULN2003AN
- 1x 16-pin socket for ULN2008AN
- 1x 2N7000 MOSFET
- 7x 110ohm resistors
- 7x 150ohm resistors
- 1x 4000ohm resistor
- 1x 800ohm resistor
- 3x RJ45 crimps
- 3x Sparkfun RJ45 jacks https://www.sparkfun.com/products/643
- 3x Sparkfun RJ45 breakout boards https://www.sparkfun.com/products/716

### Wiring
- 1x a bunch of scrap CAT5 to salvage solid wiring from
- 1x some scrap 18GA wire https://www.amazon.com/gp/product/B0154MAECC/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1
- 1x 40pin IDE cable
- 1x pair of male and female barrel connectors https://www.amazon.com/gp/product/B01G6EAY0E/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1

### Raspberry Pi 3
- Raspberry Pi 3 single board computer https://www.raspberrypi.com/products/raspberry-pi-3-model-b-plus/
- 8GB SD card https://www.amazon.com/gp/product/B000WH6H1M/ref=oh\_aui\_detailpage\_o01\_s00?ie=UTF8&psc=1

### Enclosures
- 1x Hammond case https://www.amazon.com/gp/product/B0002BSRIO/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1
- 1x Raspberry Pi case with GPIO header access https://www.amazon.com/gp/product/B00MQWQT0A/ref=oh\_aui\_search\_detailpage?ie=UTF8&psc=1

### Fit and finish
- 1x 3M double-sided tape
- 1x JB Weld
- 1x tinted acrylic https://www.amazon.com/gp/product/B01A1C16TK/ref=oh\_aui\_detailpage\_o02\_s00?ie=UTF8&psc=1

Things I would do differently
=============================
-   Prototype on a breadboard first.
-   Make sure the IC’s selected have the appropriate number of pins. The sink driver had seven pairs of inputs and outputs, and I needed eight.
-   Pay more attention to cable lengths. I would’ve liked to locate the RPi either above or below the LED driver enclosure instead of on top of it. That’s the only place it can be because of the length I trimmed the IDE cable to.
-   Locate the LED driver enclosure on top of the hole in the sign. This way I could run cabling from the LED panels straight into the enclosure without exposing the cables at all.
-   Use stackable pin headers for the resistors. Trial-and-error’ing resistor values to tweak the brightness could happen quicker. That and I can replace them in the field should the values I chose turn out to be too bright or too dim.

Thank you
=========
Thanks to my two engineer friends, Rick Nemer and [@gyrowoof](http://www.twitter.com/gyrowoof), who I consulted heavily with for selecting IC’s and design of the LED driver board. Rick actually donated the IC’s and resistors to the project since he had a bunch of them handy.

Also thanks to Rototron, who helped on the Python script based from his 7 Segment LED tutorial:

http://www.rototron.info/7-segment-led-tutorial-for-raspberry-pi/

Inspired by this fine sign from Vectorama and Assembly, which are large LAN party events in Finland:

https://www.reddit.com/r/lanparty/comments/4gjz3r/bandwidth\_display/
