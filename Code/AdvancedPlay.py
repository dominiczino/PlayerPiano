import mido
from mido import MidiFile
import serial
import time

waitForAllMsgs=True #Keep this true

config=open("config.txt")

COMport=config.readline().split()[1]
rateHeat=float(config.readline().split()[1]) #Heat accumulation speed
rateCool=float(config.readline().split()[1]) #Cooldown speed
rateMult=float(config.readline().split()[1])  #Multiplier to the rate for heat at Darlington-level
overheatWarn=float(config.readline().split()[1]) # percent heat level to warn (set to 100 to disable warnings)
overheatStop=float(config.readline().split()[1]) # percent heat to disable a note (set to 100 to never disable notes)
offlineMode=bool(int(config.readline().split()[1])) #Doesn't try to connect to an arduino if true

#Error Messages
overdue=bool(int(config.readline().split()[1]))
fastCommands=bool(int(config.readline().split()[1]))
shortNote=bool(int(config.readline().split()[1]))
outOfRange=bool(int(config.readline().split()[1]))
errNote=bool(int(config.readline().split()[1]))
pedalMsgs=bool(int(config.readline().split()[1]))





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
        return bit


if not offlineMode:
    print("Opening COM port...")
    try:
        ser=serial.Serial(COMport,baudrate=115200,timeout=1)
    except:
        ser.close()
        ser=serial.Serial(COMport,baudrate=115200,timeout=1)
    print("Opened.")

    time.sleep(2) #Needed because opening the port takes some time


    ser.write(bytes([5])) #Make sure the arduino is doing what it should be

    print("Checking Arduino Communication...")
    if int(ser.read().hex(),16)==2:
        print("Good")
    else:
        print("BAD")
        
try:
    if bool(int(input("Advanced mode? 1|0: "))):
        print("Advanced mode activated...")
        advanced=True
    else:
        print("Standard mode...")
        advanced=False
except:
    print("Standard mode...")
    advanced=False

running=True
while(running):
    fileSet=False
    while not fileSet:
        try:
            filename=input("Enter MIDI filename (including extension), or EXIT: ")
            if filename=="EXIT":
                raise KeyboardInterrupt
            else:
                mid = MidiFile(filename)
                fileSet=True
        except KeyboardInterrupt:
            raise ValueError("User ended")
        except:
            print("Try again...")

    tempoSet=False
    tempo_multiplier=1
    while advanced and not tempoSet:
        try:
            tempo_multiplier=float(input("Enter speed multiplier (1=full speed): "))
            tempoSet=True
        except KeyboardInterrupt:
            raise ValueError("User ended")
        except:
            pass

    mid.ticks_per_beat*=tempo_multiplier

    try:
        print("Playing")
        cumOverageMinor=0
        cumOverageMajor=0
        noteTimes=[0 for i in range(96)]
        notestates=[0 for i in range(96)] #0 is no action. 1 is turning on, 2 is turning off
        heats=[0 for i in range(96)] #100 is max heat, 0 is no heat
        blacklist=[False for i in range(96)] #if true, that note cannot be turned on

        startTime=time.time()
        heatClock=startTime
        ref=0
        for msg in mid:
            span=time.time()-heatClock
            if span>0.1:
                for bit in range(96):
                    bundleBit=bit+7-(bit%8)
                    if noteTimes[bit]>0: #if the note is being played
                        heats[bit]+=rateHeat*(100-heats[bit])*int(span/0.1)
                        heats[bundleBit]+=rateHeat*(100-heats[bundleBit])*int(span/0.1)*rateMult
                        if heats[bit]>overheatStop:
                            print("[OVERHEAT] Bit {} has overheated and has been shut down".format(bit))
                            blacklist[bit]=True
                            notestates[bit]=2
                            noteTimes[bit]=0
                            data=bytes("{},{},".format(0,bit),'ascii')
                            ser.write(data)
                            ser.read()
                        elif heats[bit]>overheatWarn:
                            print("[HEAT WARNING] Bit {} is getting hot! At {}%".format(bit,heats[bit]))

                        if heats[bundleBit]>overheatStop:
                            print("[MAJOR OVERHEAT] Darlington {} has overheated and has been shut down".format(int(bundleBit/8)))
                            blacklist[bundleBit]=True
                        elif heats[bundleBit]>overheatWarn:
                            print("[HEAT WARNING] Darlington {} is getting hot! At {}%".format(int(bundleBit/8),heats[bundleBit]))
                    else:
                        heats[bit]-=rateCool*heats[bit]*int(span/0.1)
                        heats[bundleBit]-=rateCool*heats[bundleBit]*int(span/0.1)*rateMult
                    if heats[bit]<overheatWarn:
                        blacklist[bit]=False
                heatClock=time.time()
            if waitForAllMsgs or msg.type=='note_off' or msg.type=='note_on':
                if ref==0:
                    ref=time.time()
                if msg.time>0:
                    currentTime=time.time()
#                    for i in range(88):
#                        if notestates[i]==1:
#                            noteTimes[i]=currentTime
#                            notestates[i]=0
#                        elif notestates[i]==2:
#                            duration=currentTime-noteTimes[i]
#                            noteTimes[i]=0
#                            notestates[i]=0
#                            if duration<0.005 and errNote:
#                                print("[ERRONEOUS NOTE?] note {} at time {}, (note time {})".format(msg.note,time.time()-startTime,msg.time))
#                            elif duration<0.05 and shortNote:
#                                print("[SHORT NOTE], Note was only {0:.3f} sec long at time {1}".format(duration,time.time()-startTime))


                    elapsed=time.time()-ref
                    if elapsed>msg.time:
                        if msg.time<0.02:
                            pass
                            cumOverageMinor+=elapsed-msg.time
                            if fastCommands:
                                print("[FAST COMMANDS] {0:.3f}sec behind on a {1:.3f}sec demand".format(elapsed-msg.time,msg.time))
                        else:
                            cumOverageMajor+=elapsed-msg.time
                            if overdue:
                                print("[OVERDUE] {0:.3f}sec behind on a {1:.3f}sec demand".format(elapsed-msg.time,msg.time))
                    else:
                        while(time.time()-ref<=msg.time):
                            time.sleep(0.003)
                    ref=time.time()

            if msg.type=='control_change' and pedalMsgs:
                if msg.control==64:
                    if msg.value>64:
                        print("[PEDAL] Depressed")
                    else:
                        print("[PEDAL] Lifted")

            if msg.type=='note_off':
                pnote=midiToBit(msg.note)
                notestates[pnote]=2
                if offlineMode:
                    print("{},{},".format(0,pnote))
                else:
                    data=bytes("{},{},".format(0,pnote),'ascii')
                    ser.write(data)
                    ser.read()
            if msg.type=='note_on':
                pnote=midiToBit(msg.note)
                if msg.velocity==0:
                    notestates[pnote]=2
                    if offlineMode:
                        print("{},{},".format(0,pnote))
                    else:
                        data=bytes("{},{},".format(0,pnote),'ascii')
                        ser.write(data)
                        ser.read()
                else:
                    if not blacklist[pnote]:
                        bundleBit=pnote+7-(pnote%8)
                        if not blacklist[bundleBit]:
                            notestates[pnote]=1
                            if offlineMode:
                                print("{},{},".format(1,pnote))
                            else:
                                data=bytes("{},{},".format(1,pnote),'ascii')
                                ser.write(data)
                                ser.read()
                        else:
                            print("[BLACKLIST] Cannot play note {} due to Darlington-level blacklisting ({} heat)".format(pnote, heats[bundleBit]))
                    else:
                        print("[BLACKLIST] Cannot play note {} due to blacklisting ({} heat)".format(pnote, heats[pnote]))


        endTime=time.time()
        print("")
        print("***Song Complete***")
        print("")
#
#        print("TOTAL OVERDUE TIME: {0:.3f}".format(cumOverageMajor+cumOverageMinor))
#        print("    Major Part: {0:.3f}".format(cumOverageMajor))
#        print("    Minor Part: {0:.3f}".format(cumOverageMinor))
        
    except KeyboardInterrupt: #Try to gracefully turn off all the notes before stopping
        if not offlineMode:
            for pnote in range(96):
                data=bytes("{},{},".format(0,pnote),'ascii')
                ser.write(data)
                ser.read()

        #ser.close()
        print("Song Terminated")
        #raise ValueError("Execution gracefully terminated")
    answered=True
    while not answered:
        try:
            running=bool(int(input("Play another song? (1 for yes, 0 for no):")))
            answered=True
        except:
            pass
if not offlineMode:
    ser.close()




