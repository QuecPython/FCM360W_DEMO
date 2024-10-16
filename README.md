## Platform account

## Distribution network process

**SSID of distribution network**
ap_ssid="quecpython-fcm360w"
ap_password="12345678"

**Distribution network address**
10.10.10.1:80 

**Equipment startup process**

- SSID connected to the distribution network after device startup
- After the distribution network, the SSID is saved in the wifi. json file
- After restarting the device, it will connect to the SSID configured in wifi. json
- After connecting to WiFi, QuecIOT will be connected
- Continuous transmission of temperature and humidity data to the cloud in transparent mode
- Logging into the cloud allows you to view the uploaded data information of the device
