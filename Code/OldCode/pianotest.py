# -*- coding: utf-8 -*-
"""
Created on Fri Dec 13 13:37:13 2019

@author: Dominic
"""

#import os
#import mido
#import usb.core
from mido import MidiFile
import serial
import time

ser=serial.Serial("COM13",baudrate=115200,timeout=2)
time.sleep(3)

for i in range(8):
    byte=bytes([pow(2,i)])
    ser.write(byte)
    print(int(byte.hex(),16))
    print(int(ser.read().hex(),16))
    print("")
ser.close()


