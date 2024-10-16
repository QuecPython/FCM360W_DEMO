import ql_fs
import uos
if ql_fs.path_exists("usr/qth_config.ini"):
    uos.remove("usr/qth_config.ini")
if ql_fs.path_exists("usr/qth_config_bak.ini"):
    uos.remove("usr/qth_config_bak.ini")
from usr import qth_config
from usr import qth_bus
from usr import qth_dmp
import modem
import usocket as socket
import utime as time
import network
import osTimer
import _thread
import ure
import gc
import ujson



nic = network.WLAN(network.AP_MODE)

class QPY_WebConfig(object):
    def __init__(self, 
                 ap_ssid="quecpython-fcm360w",
                 ap_password="12345678",
                 server_ip="0.0.0.0",
                 server_port=80,
                 timeout=0,
                 callback=None
                 ):
        self.ap_ssid = ap_ssid + "-" + modem.getDevMAC().replace(":", "")
        self.ap_password = ap_password
        self.server_ip = server_ip
        self.server_port = server_port
        self.finish_callback = callback 

        self.nic_connect_status = False
        self.stop_status = False

        self.ap_data = None
        self.task_id = None
        self.socket = None
        self.client = None
        self.request = b''

        self.timeout = timeout
        self.timeout_timer = osTimer()


    def send(self, client, content, status_code=200):
        _len = len(content)

        header = "HTTP/1.0 {} OK\r\n".format(status_code)
        header += "Content-Type: text/html\r\n" 
        header += "Content-Length: {}\r\n\r\n".format(_len)
        
        client.sendall(header)
        if _len > 0: client.sendall(content)


    def webconfig_timeout(self):
        print("webconfig timeout, will stop state machine.")
        self.stop()


    def webconfig_task(self):
        ip = port = None
        while True:
            try:
                self.client, ip, port = self.socket.accept()
                print("[client address] ip=%s, port=%d " % (ip, port))
                self.client.settimeout(5)
                self.request = b""
                try:
                    while "\r\n\r\n" not in self.request:
                        self.request += self.client.recv(512)
                except Exception as e:
                    print("webconfig recv error:",e)
                print("request:",self.request)
                self.ap_data = parse_cfg_from_http(self.request)
                print(self.ap_data)
                if False != self.ap_data and None != self.ap_data and 2 == len(self.ap_data):  
                    self.send(self.client, html_cfg_page(True) )
                    time.sleep_ms(20)
                    if None != self.finish_callback: 
                        if False != self.ap_data and None != self.ap_data and 2 == len(self.ap_data): 
                            f = open("usr/wifi.json", "w")
                            ujson.dump({'wifi': {'ssid': self.ap_data[0], 'passwd': self.ap_data[1]}}, f)
                            f.close()
                            # self.finish_callback(self.ap_data[0], self.ap_data[1])
                            time.sleep(1)
                            from misc import Power 
                            Power.powerRestart()  # restart to connect wifi
                    self.task_id = None
                    _thread.stop_thread(0)
                else:
                    self.send(self.client, html_cfg_page(False) )
                    time.sleep_ms(20)
                    self.client.close()
                    self.client = None
            except Exception as e:
                print("webconfig accept task error:", e)


    def start_once(self):
        print("start")
        self.stop()
        try:
            wifi_info = ujson.loads(open("usr/wifi.json", "r").read())
            print(wifi_info)
        except:
            wifi_info = None
        if wifi_info: 
            self.finish_callback(wifi_info["wifi"]["ssid"], wifi_info["wifi"]["passwd"])
            return
        global nic
        nic.mode(network.AP_MODE) 
        nic.config(ap_ssid=self.ap_ssid, ap_password=self.ap_password)
        nic.active(True)
        self.nic_connect_status = True
        time.sleep_ms(50)
        if self.timeout != 0: self.timeout_timer.start(self.timeout * 1000, 0, self.webconfig_timeout)

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP_SER)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.server_ip, self.server_port))
            self.socket.listen(1)
            
            _thread.stack_size(2 * 1024)
            self.task_id = _thread.start_new_thread(self.webconfig_task, ())
            self.stop_status = True
        except Exception as e:
            self.task_id = None
            print("webconfig start error:", e)
            return
        
        print("nic mode:{}  wifi-name:{}  wifi-pwd:{}  ifconfig:{}".format(nic.mode(), self.ap_ssid, self.ap_password, nic.ifconfig()))
        print("webconfig start success. ip address: http://{}:{}/\n".format(nic.ifconfig()[0],  self.server_port))


    def stop(self):
        if not self.stop_status: return
        try:
            if None != self.task_id: _thread.stop_thread(self.task_id)
            self.task_id = None
            if None != self.socket: self.socket.close() 
            self.socket = None
            if self.nic_connect_status: nic.disconnect() 
            self.nic_connect_status = False
            if None != self.timeout_timer: self.timeout_timer.stop()

            print("webconfig stop success.")
            self.stop_status = False
            gc.collect()
        except Exception as e:
            print("webconfig close error:", e)

            
def parse_cfg_from_http(request):
    http_str ={
        "+": " ",
        "%22": '"',
        "%23": "#",
        "%25": "%",
        "%26": "&",
        "%28": "(",
        "%29": ")",
        "%2B": "+",
        "%2C": ",",
        "%2F": "/",
        "%3A": ":",
        "%3B": ";",
        "%3C": "<",
        "%3D": "=",
        "%3E": ">",
        "%3F": "?",
        "%40": "@",
        "%5C": "\\",
        "%7C": "|",   
    }
    match = ure.search("ssid=([^&]*)&password=(.*)", request)
    if match is None:  return False
    try:
        ssid = match.group(1).decode("utf-8")
        password = match.group(2).decode("utf-8")
        for key, value in http_str.items():
            ssid = ssid.replace(key, value)
            password = password.replace(key, value)
    except Exception:
        ssid = match.group(1).decode("utf-8")
        password = match.group(2).decode("utf-8")
        for key, value in http_str.items():
            ssid = ssid.replace(key, value)
            password = password.replace(key, value)

    if len(ssid) == 0: return False
    return (ssid, password)

def html_cfg_page(status=False):
    if status:
        return """<html>
                    <head>
                        <title>QuecPython WebConfig</title>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1">
                    </head>
                    <body>
                        <h1>Wi-Fi distribution network successful!</h1>
                    </body>
                </html>"""      
    
    return """<html>
                <head>
                    <title>QuecPython WebConfig</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                </head>
                <body>
                    <h1>Wi-Fi distribution network</h1>
                    <form action="configure" method="post">
                        <div>
                            <label>SSID</label>
                            <input type="text" name="ssid">
                        </div>
                        <div>
                            <label>PASSWORD</label>
                            <input type="password" name="password">
                        </div>
                        <input type="submit" value="Connect">
                    <form>
                </body>
            </html>"""
            

def connect_wifi(ssid, passwd):
    print("connect wifi:", ssid, passwd)
    nic.mode(network.STA_MODE)
    result_code = nic.connect(ssid=ssid, password=passwd, timeout=30)
    print("connect wifi result:", result_code)

    if result_code == 2000:
        init()
        qth_config.setProductInfo('*****','*************')
        qth_config.setServer('iot-south.quecteleu.com:1883')
        eventCb={
            'devEvent':App_devEventCb, 
            'recvTrans':App_cmdRecvTransCb, 
            }
        qth_config.setEventCb(eventCb)
        start()
        print("connect mqtt success")
        # while True:
        #     ret = qth_bus.sendTrans(1, "temperature:25&humidity:60")
        #     time.sleep(60)
        #     gc.collect()
    else:
        print("connect wifi fail")


_qth_isRun = -1


def init():
    global _qth_isRun
    print('Qth.init')
    if(-1 != _qth_isRun):
        return True
    qth_config.init()
    qth_dmp.init()

# 打印输出初始化信息
    devInfo = qth_bus.getDevInfo([2, 11])
    print('QthSDK\t:{}'.format(devInfo[11]))
    print('FW VER\t:{}'.format(devInfo[2]))
    print('serUrl\t:{}'.format(qth_config._config_url))
    print('PK\t:{}'.format(qth_config._config_pk))
    print('DK\t:{}'.format(modem.getDevMAC().replace(":","")))

    _qth_isRun = 0
    return True

def start():
    global _qth_isRun
    ret = False
    def _run():
        while(1 == _qth_isRun):
            sleep_time = 0
            if ''==qth_config._config_ds:
                sleep_time = qth_dmp.register(qth_config._config_url, 120, qth_config._config_pk, qth_config._config_ps, modem.getDevMAC().replace(":",""))
            else:
                sleep_time = qth_dmp.login(qth_config._config_url, 120, qth_config._config_pk, qth_config._config_ps, modem.getDevMAC().replace(":",""), qth_config._config_ds)
            
            if sleep_time > 0:
                time.sleep(sleep_time)

    if(0 == _qth_isRun):
        _qth_isRun = 1
        try:
            pid = _thread.start_new_thread(_run,())
            ret = True
        except Exception as e:
            print('start run Exception:{}'.format(e))
    return ret


def App_devEventCb(event, result):
    print('dev event:{} result:{}'.format(event, result))

def App_cmdRecvTransCb(value):
    ret = qth_bus.sendTrans(1, value)
    print('recvTrans value:{} ret:{}'.format(value, ret))

def Qth_tslSend():
    static_var = 0
    while True:       
        # 先判断连接云平台状态
        if qth_dmp.state():
            static_var+=1
        time.sleep(30)


if __name__ == '__main__':
    web_cfg = QPY_WebConfig(callback=connect_wifi)
    web_cfg.start_once()

    
    
    
    
    