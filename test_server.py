#!/usr/bin/env python

import socket

localIP     = "127.0.0.1"
localPort   = 3636

def welcome():
    return "Lightpack API v1.4 - Prismatik API v2.2 (type 'help' for more info)\n"

# getcolors
# colors:0-5,255,1;1-1,255,9;2-1,255,22;3-1,255,35;...
leds = 10
color = '255,255,255'
def getcolors():
    colors = ";".join([f"{idx}-{color}" for idx in range(leds)])
    return f"colors:{colors};\n"

# getstatus
# status:on
status = "on"
def getstatus():
    return f"status:{status}\n"

# getbrightness
# brightness:100
brightness = 100
def getbrightness():
    return f"brightness:{brightness}\n"

profiles = ['Lightpack']
profile_idx = 0
# getprofile
# profile:hassio
def getprofile():
    return f"profile:{profiles[profile_idx]}\n"

# getprofiles
# profiles:hassio;Lightpack;
def getprofiles():
    return f"profiles:{';'.join(profiles)};\n"

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((localIP, localPort))
s.listen(4)
client, addr = s.accept()
client.sendall(welcome().encode('ascii'))
try:
    while True:
        data, addr = client.recvfrom(128*1024)
        req = data.decode('ascii').strip()
        resp = globals()[req]()
        print(resp.strip())
        client.sendall(resp.encode('ascii'))
except:
    pass
finally:
    s.close()
