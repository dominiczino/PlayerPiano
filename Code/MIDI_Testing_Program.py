import mido
from mido import MidiFile
import serial
import serial.tools.list_ports as serialPorts
import time
import os

#Error Messages
overdue=True #bool(int(config.readline().split()[1]))
resetWarnings=False
heatWarnings=True
midiNumDict=dict()

I_am_speed=True

rootSongPath="Songs\\"
rootPlaylistPath="Playlists\\"
songSpeeds=dict()
timeNum=0
alias=dict()
notetimes=[]
noteTemps=[]
noteMaxTemps=[]
noteStates=[]

for x in range(89):
    notetimes.append(0)
    noteTemps.append(80)
    noteMaxTemps.append(80)
    noteStates.append(False)



highPowerTime=0.025 #Time to wait for the high-current initial state
shiftTime=0.005#Time it takes the shift registers to shift-out




############################################################################
#Convert a midi note number into the bit number
def midiToBit(note):
    pianoNote=note-20
    bitA=84-pianoNote
    if bitA==7:
        bit=  8
    elif bitA>0:
        byte=int(bitA/7)
        bit = bitA+byte
    else:
        bit = bitA

    if bit%8==7:
        print("[OUT OF RANGE] Tried to play null bit {}".format(bit))
        return 0

    if bit>=96 or bit<0:
        print("[OUT OF RANGE ERROR] tried to push bit {}".format(bit))
        return 0
    else:
        midiNumDict[bit]=note
        return bit


def updateTemps(timeStep,timeNumBoi):
    heatCapacity=4 #J/F
    roomTemp=80 #F
    coolingFactor=0.017391 #W/F
    heatingRate=6.5 #OVERWRITTEN IN LOOP!!!

    for i in range(len(noteTemps)):
        #heatingRate=7.5241-0.0091*noteTemps[i]
        netPower=heatingRate*noteStates[i]-coolingFactor*(noteTemps[i]-roomTemp)
        noteTemps[i]+=netPower*timeStep/heatCapacity
        noteMaxTemps[i]=max([noteMaxTemps[i],noteTemps[i]])

        if noteTemps[i]>250:
            print('\033[91m'+"[F I R E] Note {0:.0f} has caused the piano to combust! ({1:.1f} deg F)".format(i,noteTemps[i])+'\033[0m')
        elif noteTemps[i] > 180:
            print('\033[91m'+"[HEAT DANGER] Note {0:.0f} is very hot! ({1:.1f} deg F)".format(i,noteTemps[i])+'\033[0m')
        elif noteTemps[i] > 140:
            print('\033[93m'+"[WARM] Note {0:.0f} is getting kinda toasty ({1:.1f} deg F)".format(i,noteTemps[i])+'\033[0m')
    displayTempsBetter(timeNumBoi)


def displayTempsBetter(timeNumBoi):
    thiccStr=""
    cutoff=250
    inc=10
    while(cutoff>70):
        if cutoff>=100:
            thiccStr+=str(cutoff)+" "
        else:
            thiccStr+=" {} ".format(cutoff)
        for i in range(1,len(noteTemps)):
            temp=noteTemps[i]
            if temp>=cutoff:
                if cutoff>=210:
                    thiccStr+="\033[91m"+'O'+"\033[0m"
                elif cutoff>=140:
                    thiccStr+="\033[93m"+'*'+"\033[0m"
                else:
                    thiccStr+="|"
            else:
                thingy=cutoff-noteMaxTemps[i]
                if thingy<inc and thingy>0:
                    thiccStr+="_"
                else:
                    thiccStr+=" "
        thiccStr+="\n"
        cutoff-=inc
    #Make keystrike indicators
    thiccStr+="   \033[92m"
    for playing in noteStates:
        if playing:
            thiccStr+='*'
        else:
            thiccStr+=" "
    thiccStr+="\033[0m\n"


    #Make note numbers and timestamp
    thiccStr+="    "
    for i in range(1,len(noteTemps)):
        thiccStr+=str(i%10)
    timeNumBoi=int(timeNumBoi)
    minutes=int(timeNumBoi/60)
    seconds=timeNumBoi%60
    if seconds<10:
        thiccStr+="\n{}:0{}         ".format(minutes,seconds)
    else:
        thiccStr+="\n{}:{}         ".format(minutes,seconds)
    for i in range(1,9):
        thiccStr+="{}         ".format(i)
    thiccStr+="\n"
    print(thiccStr)
    time.sleep(0.005)

    
######################################################################
def findCOMport():
    #List all open COM ports
    ports=serialPorts.comports()
    for port in ports:
        if "Arduino Uno" in port[1]:
            print("Successfully found Arduino on {}".format(port[0]))
            return port[0]
    print("Failed to find the COMport, please enter one from the list below, or close the program and try again")
    for port in ports:
        print(port[1])
    return input("Enter full name of port: ")


#####################################################################
def timeFunc():
    #Returns the current time
    #This function is just to provide a single place to change the choice of underlying function
    return time.perf_counter()

######################################################################
#This should be the full file path, this will not add the root string
def playSong(filename,shortname):
    overdueCount=0
    overdueTotal=0
    timeNum=0
    nonresetCount=0
    print('\033[93m'+"[INFO] Playing with High-Current Period of {}ms".format(highPowerTime*1000)+'\033[0m')
    print('\033[93m'+"[INFO] Playing with Shift-Delay of {}ms".format(shiftTime*1000)+'\033[0m')
    highpowerflag=False
    changeflag=False
    try:
        mid=MidiFile(filename)
        if shortname in songSpeeds:
            mid.ticks_per_beat*=songSpeeds[shortname]
            print("Speed overridden to {}x".format(songSpeeds[shortname]))
        print("Playing {}".format(shortname))
        startTime=timeNum#timeFunc()
        ref=0
        for msg in mid:
            if ref==0:
                ref=timeNum#timeFunc()
            if msg.time>0.005:
                if heatWarnings:
                    updateTemps(msg.time,timeNum)
                if highpowerflag:
                    #time.sleep(highPowerTime) #Time for High Power Delay
                    highpowerflag=False
                if changeflag:
                    #time.sleep(shiftTime) #Shift Register Delay
                    changeflag=False
                currentTime=timeNum#timeFunc()
                elapsed=timeNum-ref #&&&&&
                if elapsed>msg.time:
                    if msg.time>0.01:
                        a=elapsed-msg.time
                        ratio=a/(msg.time+0.001)*100
                        overdueTotal+=a
                        overdueCount+=1
                        if ratio<75 and overdue:
                            print("[OVERDUE] {0:.3f}sec behind on a {1:.3f}sec demand ({2:.1f}%)".format(a,msg.time,ratio))
                        elif overdue:
                            print('\033[91m'+"[OVERDUE] {0:.3f}sec behind on a {1:.3f}sec demand ({2:.1f}%)".format(a,msg.time,ratio)+'\033[0m')
                else:
                    while(timeNum-ref<=msg.time): #&&&&&&&&&&
                        if I_am_speed:
                            timeNum=timeNum+0.005
                        else:
                            time.sleep(0.005)
                            timeNum=timeFunc()
                ref=timeNum #timeFunc()

            if msg.type=='control_change':
                if msg.control==64:
                    if msg.value>64:
                        pass #Pedal pressed commands
                    else:
                        pass #Pedal lifted commands

            if msg.type=='note_off':
                pnote=midiToBit(msg.note)
                data=bytes("{},{},".format(0,pnote),'ascii')
                #ser.write(data)
                #ser.read()
                changeflag=True
                notetimes[msg.note-20]=timeNum#timeFunc()
                noteStates[msg.note-20]=False
            if msg.type=='note_on':
                pnote=midiToBit(msg.note)
                if msg.velocity==0:
                    data=bytes("{},{},".format(0,pnote),'ascii')
                    #ser.write(data)
                    #ser.read()
                    changeflag=True
                    notetimes[msg.note-20]=timeNum#timeFunc()
                    noteStates[msg.note-20]=False
                else:
                    data=bytes("{},{},".format(1,pnote),'ascii')
                    #ser.write(data)
                    #ser.read()
                    highpowerflag=True
                    changeflag=True
                    noteStates[msg.note-20]=True
                    dT=timeNum-notetimes[msg.note-20]  #timeFunc()
                    if dT < 0.025:
                        nonresetCount+=1
                        if dT<0.001 and resetWarnings:
                            print('\033[91m'+"[RESET] Note was not released!"+'\033[0m')
                        elif resetWarnings:
                            print('\033[91m'+"[RESET] Note was not released for long enough! Only {0:3f}sec".format(dT)+'\033[0m')

        print("")
        print("***Song Complete***")
        print("Overdue on {} notes, for total time lag of {}s".format(overdueCount,overdueTotal))
        print("Failure to Reset on {} notes".format(nonresetCount))
        print("")
    #except Exception as inst:
    #    print("A fatal error has occured while trying to play {}".format(filename))
    #    print("Error details below: ")
    #    print(inst)
    except KeyboardInterrupt:
        for pnote in range(96):
            data=bytes("{},{},".format(0,pnote),'ascii')
            #ser.write(data)
            #ser.read()
        raise ValueError("Keyboard Interrupt Triggered")
    for pnote in range(96):
        data=bytes("{},{},".format(0,pnote),'ascii')
        #ser.write(data)
        #ser.read()


########################################################
def loadSpeeds():
    spds=open("SongSpeeds.txt")
    for line in spds:
        data=line.split(";")
        songSpeeds[data[0]]=float(data[1])
        print("\t Noted special speed of {}x for song {}".format(float(data[1]),data[0]))
        
########################################################
def loadAlias():
    aliasfile=open("aliases.txt")
    for line in aliasfile:
        data=line.split(";")
        alias[data[0]]=data[1]
        print("\t Alias added mapping {} to {}".format(data[0],data[1]))


#########################MAIN EXECUTION###############################
##=========================================================================================
print("loading override speeds")
loadSpeeds()

print("loading aliases")
loadAlias()

#print("Opening COM port...")
os.system('color')
#COMport = findCOMport()
try:
    pass
    #ser=serial.Serial(COMport,baudrate=115200,timeout=0.5)
except:
    pass
    #ser.close()
    #ser=serial.Serial(COMport,baudrate=115200,timeout=0.5)
#print("Opened.")

#time.sleep(2) #Needed because opening the port takes some time


#jhgser.write(bytes([5])) #Make sure the arduino is doing what it should be

print("Checking Arduino Communication...")
##if int(ser.read().hex(),16)==2:
    #print("Good")
#else:
    #print("BAD")



runType=None
while runType is None:
    try:
        entry=input("Do you want to play single songs or a playlist: (SONG or PLAYLIST): ")
        if entry=="SONG":
            runType="song"
        elif entry=="PLAYLIST":
            runType="playlist"
    except:
        print("Failed to parse input, try again")
    else:
        if runType is None:
            print("Failed to parse input, try again")

if runType=="song":
    fileSet=False
    while not fileSet:
        try:
            filename=input("Enter MIDI filename (excluding extension), or EXIT: ")
            if filename=="EXIT":
                raise KeyboardInterrupt
            else:
                if filename in alias:
                    filename=alias[filename]
                shortname=filename
                filename=rootSongPath+filename+".mid"
                mid=MidiFile(filename)
                fileSet=True
        except KeyboardInterrupt:
            raise ValueError("User ended")
        except:
            print("Try again...")

    playSong(filename,shortname)
    playSong(filename,shortname)
else: #This is the playlist part
    fileSet=False
    while not fileSet:
        try:
            filename=input("Enter playlist name, or EXIT: ")
            if filename=="EXIT":
                raise KeyboardInterrupt
            else:
                filename=rootPlaylistPath+filename+".txt"
                playlist=open(filename)
                fileSet=True
        except KeyboardInterrupt:
            raise ValueError("User ended")
        except:
            print("Try again...")

    for song in playlist:
        try:
            song=song.rstrip()
            if song in alias:
                filename=alias[filename]
            else:
                filename=song
            shortname=filename
            filename=rootSongPath+filename+".mid"
            mid=MidiFile(filename)
            playSong(filename,shortname)
        except KeyboardInterrupt:
            raise ValueError("user canceled playing")
        except:
            print("Could not find song {}".format(song))

#ser.close()

print("imma head out")
time.sleep(3)