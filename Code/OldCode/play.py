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


offlineMode=True

if not offlineMode:
    print("Opening COM port...")
    ser=serial.Serial("COM13",baudrate=115200,timeout=0.5)

    time.sleep(4) #Needed because opening the port takes some time


    ser.write(bytes([5])) #Make sure the arduino is doing what it should be

    print("Checking Arduino Communication...")
    if int(ser.read().hex(),16)==2:
        print("Good")
    else:
        print("BAD")


filename=input("Enter MIDI filename, including extension: ")
mid = MidiFile(filename)

#1-84 on piano
#21-104 midi

print("Playing")
for msg in mid.play():
    if msg.type=='note_off':
        pnote=msg.note-20
        pnote=88-pnote
        if not(pnote>84 or pnote <0): #ensure note in range of piano
            if offlineMode:
                print("{},{},".format(0,pnote))
            else:
                ser.write(bytes("{},{},".format(0,pnote),'ascii'))
    if msg.type=='note_on':
        pnote=msg.note-20
        pnote=88-pnote
        if msg.velocity==0:
            if not(pnote>84 or pnote <0): #ensure note in range of piano
                if offlineMode:
                    print("{},{},".format(0,pnote))
                else:
                    ser.write(bytes("{},{},".format(0,pnote),'ascii'))
        else:
            if not(pnote>84 or pnote <0): #ensure note in range of piano
                if offlineMode:
                    print("{},{},".format(1,pnote))
                else:
                    ser.write(bytes("{},{},".format(1,pnote),'ascii'))
            else:
                print("Tried to play out-of-range note ({})".format(pnote))

print("Song Complete")
ser.write(4)
ser.close()


