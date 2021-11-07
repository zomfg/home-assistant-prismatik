#!/usr/bin/env python
"""Smol test server mimicking Prismatik"""
import socket

LOCAL_IP   = "127.0.0.1"
LOCAL_PORT = 3636

def welcome():
    """prismatik api welcome message"""
    return "Lightpack API v1.4 - Prismatik API v2.2 (type 'help' for more info)\n"

LEDS = 10
COLOR = '255,255,255'
def getcolors():
    """
    getcolors
    colors:0-5,255,1;1-1,255,9;2-1,255,22;3-1,255,35;...
    """
    colors = ";".join([f"{idx}-{COLOR}" for idx in range(LEDS)])
    return f"colors:{colors};\n"

STATUS = "on"
def getstatus():
    """
    getstatus
    status:on
    """
    return f"status:{STATUS}\n"

BRIGHTNESS = 100
def getbrightness():
    """
    getbrightness
    brightness:100
    """
    return f"brightness:{BRIGHTNESS}\n"

PROFILES = ['Lightpack','Призматик','Regnbåge']
PROFILE_IDX = 0
def getprofile():
    """
    getprofile
    profile:hassio
    """
    return f"profile:{PROFILES[PROFILE_IDX]}\n"

def getprofiles():
    """
    getprofiles
    profiles:hassio;Lightpack;
    """
    return f"profiles:{';'.join(PROFILES)};\n"

# print all test responses
print(welcome(), end='')
print(getstatus(), end='')
print(getprofile(), end='')
print(getprofiles(), end='')
print(getbrightness(), end='')
print(getcolors(), end='')

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((LOCAL_IP, LOCAL_PORT))
s.listen(4)
client, addr = s.accept()
client.sendall(welcome().encode())
try:
    while True:
        data, addr = client.recvfrom(128*1024)
        req = data.decode().strip()
        resp = globals()[req]()
        # print(resp.strip())
        client.sendall(resp.encode())
except: # pylint: disable=bare-except
    pass
finally:
    s.close()
