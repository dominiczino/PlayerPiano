# -*- coding: utf-8 -*-
"""
Created on Sat Jan 11 03:15:24 2020

@author: Dominic
"""

from mido import MidiFile


minDuration=0.075 #shortest allowable note
delDuration=0.005 #notes shorter than this will just be deleted, rather than fixed
resetTime=0.01 #This is the amount of time needed after a note stops before it can be struck again


filename=input("Enter MIDI filename, including extension: ")
mid = MidiFile(filename)

newName=input("Enter name for modified file, including extension: ")
mid.save(newName)




