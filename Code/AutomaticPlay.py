import mido
from mido import MidiFile
import serial
import serial.tools.list_ports as serialPorts
import time

#Error Messages
overdue=True #bool(int(config.readline().split()[1]))

rootSongPath="Songs\\"
rootPlaylistPath="Playlists\\"
songSpeeds=dict()
alias=dict()

badNotes=[102,42]

############################################################################
#Convert a midi note number into the bit number
def midiToBitOLD(note):
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
        return bit


def midiToBit(note):
    if note>106 or note<22:
        #print("{}[OUT OF RANGE ERROR] tried to push note {}".format(time.time(),note))
        return 0

    if note in badNotes:
        pass
        ##print("{}[BAD NOTE WARNING] tried to play note {}, which is a known bad boi".format(time.time(),note))

    if note in [93,96]:
        #print("[CONJOINED NOTES] we played the conjoined notes :(")
        note=93

    bit=114-note
    if note%8==3:
        bit+=8
    return bit
    
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
    try:
        mid=MidiFile(filename)

        if shortname in songSpeeds:
            mid.ticks_per_beat*=songSpeeds[shortname]
            print("Speed overridden to {}x".format(songSpeeds[shortname]))
        else:
            try:
                songSpeed=float(input("Enter Song Speed Multiplier: "))
                mid.ticks_per_beat*=songSpeed
            except:
                print("error occured, running at normal speed")
                pass

        print("Playing {}".format(shortname))
        startTime=timeFunc()
        ref=0
        for msg in mid:
            if ref==0:
                ref=timeFunc()
            if msg.time>0:
                currentTime=timeFunc()
                elapsed=timeFunc()-ref
                if elapsed>msg.time:
                    if msg.time>0.01 and overdue:
                        print("[OVERDUE] {0:.3f}sec behind on a {1:.3f}sec demand".format(elapsed-msg.time,msg.time))
                else:
                    while(timeFunc()-ref<=msg.time):
                        time.sleep(0.003)
                ref=timeFunc()

            if msg.type=='control_change':
                if msg.control==64:
                    if msg.value>64:
                        pass #Pedal pressed commands
                    else:
                        pass #Pedal lifted commands

            if msg.type=='note_off':
                pnote=midiToBit(msg.note)
                data=bytes("{},{},".format(0,pnote),'ascii')
                ser.write(data)
                ser.read()
            if msg.type=='note_on':
                pnote=midiToBit(msg.note)
                if msg.velocity==0:
                    data=bytes("{},{},".format(0,pnote),'ascii')
                    ser.write(data)
                    ser.read()
                else:
                    if msg.note in badNotes:
                        print("{}[BAD NOTE WARNING] playing note {}, which is a known bad boi".format(time.time(),msg.note))
                    if msg.note in [93,96]:
                        print("[CONJOINED NOTES] we played the conjoined notes")
                    if msg.note>106 or msg.note<22:
                        print("{}[OUT OF RANGE ERROR] tried to push note {}".format(time.time(),msg.note))
                    data=bytes("{},{},".format(1,pnote),'ascii')
                    ser.write(data)
                    ser.read()

        print("")
        print("***Song Complete***")
        print("")
    except Exception as inst:
        print("A fatal error has occured while trying to play {}".format(filename))
        print("Error details below: ")
        print(inst)
    except KeyboardInterrupt:
        for pnote in range(96):
            data=bytes("{},{},".format(0,pnote),'ascii')
            ser.write(data)
            ser.read()
        raise ValueError("Keyboard Interrupt Triggered")
    for pnote in range(96):
        data=bytes("{},{},".format(0,pnote),'ascii')
        ser.write(data)
        ser.read()


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



def noteOn(noteNum):
    pnote=midiToBit(noteNum)
    data=bytes("{},{},".format(1,pnote),'ascii')
    ser.write(data)
    ser.read()

def noteOff(noteNum):
    pnote=midiToBit(noteNum)
    data=bytes("{},{},".format(0,pnote),'ascii')
    ser.write(data)
    ser.read()






#########################MAIN EXECUTION###############################
##=========================================================================================
print("loading override speeds")
loadSpeeds()

print("loading aliases")
loadAlias()

print("Opening COM port...")
COMport = findCOMport()
try:
    ser=serial.Serial(COMport,baudrate=115200,timeout=0.5)
except:
    ser.close()
    ser=serial.Serial(COMport,baudrate=115200,timeout=0.5)
print("Opened.")

time.sleep(2) #Needed because opening the port takes some time


ser.write(bytes([5])) #Make sure the arduino is doing what it should be

print("Checking Arduino Communication...")
if int(ser.read().hex(),16)==2:
    print("Good")
else:
    print("BAD")



runType=None
while runType is None:
    try:
        entry=input("Do you want to play single songs or a playlist: (SONG or PLAYLIST or NoteBump): ")
        if entry=="SONG":
            runType="song"
        elif entry=="PLAYLIST":
            runType="playlist"
        elif entry=="NoteBump":
            runType="note"
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
elif runType=="playlist": #This is the playlist part
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
elif runType=="note":
    noteToPlay=input("Enter note or exit:")
    while(noteToPlay!="exit"):
        try:
            noteNum=int(noteToPlay)
            timeboi=0.05
            noteOn(noteNum)
            time.sleep(timeboi)
            noteOff(noteNum)
            time.sleep(timeboi)
            noteOn(noteNum)
            time.sleep(timeboi)
            noteOff(noteNum)
            time.sleep(timeboi)
            noteOn(noteNum)
            time.sleep(timeboi)
            noteOff(noteNum)
            time.sleep(timeboi)
            noteOn(noteNum)
            time.sleep(timeboi)
            noteOff(noteNum)
            time.sleep(timeboi)
            noteOn(noteNum)
            time.sleep(timeboi)
            noteOff(noteNum)
            time.sleep(timeboi)
        except:
            print("owpsies I made a fucky wucky UwU")
        noteToPlay=input("Enter note or exit:")

ser.close()

print("imma head out")




