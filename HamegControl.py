#!/usr/bin/python3

import sys, time, math
from serial import *
import logging
#import io

class HamegControl:
  
  def __init__(self, SerialPort=None, logBool = False):
    
    self.baudrate=9600
    self.bytesize=8
    self.xonxoff=False
    self.logBool = logBool
    self.stopbits=STOPBITS_TWO
    if SerialPort == None:
      self.port = "/dev/ttyUSB0"
    else:
      self.port=SerialPort
    
  def init(self):
    """initialize connection to Keithley2700
    
      Raises: 
        * Value Error if serial port could not be opened
      Returns: 
        * True if everything worked fine
        
    """
    
    try:
      #
      #Open port
      #
      #Syntax: serial.Serial(port=None, baudrate=9600, bytesize=EIGHTBITS, parity=PARITY_NONE,
      #                      stopbits=STOPBITS_ONE, timeout=None, xonxoff=False, rtscts=False,
      #                      writeTimeout=None, dsrdtr=False, interCharTimeout=None)
      self.port = Serial(port=self.port, baudrate=self.baudrate, bytesize=self.bytesize, xonxoff=self.xonxoff, stopbits=self.stopbits, timeout=0.1)
      self.printout("Opening serial port to Hameg", "info")
      self.sio = io.TextIOWrapper(io.BufferedRWPair(self.port, self.port), newline='\r')

      
    except:
      self.printout("ValueError! Hameg port is already claimed or can not be found!", "error")
      raise ValueError("Hameg port is already claimed or can not be found!")
    
    return True

  def select(self, pChannelList):
    
    if not (pChannelList.find(',') != -1 or pChannelList == "ALL" or pChannelList == "NONE" or (self.isint(pChannelList) and int(pChannelList) < 5 and int(pChannelList) > 0)):
      print("Unknown format to select channels!")
      return -1
    self.sio.write(str("SEL {0}\r".format(pChannelList)))
    self.sio.flush()
    answer = self.sio.readline()
    print(answer)
    if pChannelList == "ALL":
      if not answer == "channel 1,2,3,4 selected\r":
        print("ERROR: unexpected answer of HM7044: {0}".format(answer))
        return -10
    elif pChannelList == "NONE":
      if not answer == "channels unselected\r":
        print("ERROR: unexpected answer of HM7044: {0}".format(answer))
        return -10
    else:
      if not answer == "channel {0} selected\r".format(pChannelList):
        print("ERROR: unexpected answer of HM7044: {0}".format(answer))
        return -10
    
    return 1
    
  def set(self, pValue, pUnit):
    
    cVoltMax = 32
    cCurrMax = 3
    cCurrMin = 0.005
    
    if(pUnit == "V"):
      if float(pValue) > 32 or float(pValue) < 0:
        print("ERROR: Voltage value higher than allowed maximum (32 V) or smaller than minium (10 mV)")
        return -2 
      #self.port.write("SET {0:2.2f} V\r".format(pValue).encode())
      self.sio.write(str("SET {0:2.2f} V\r".format(pValue)))
      self.sio.flush()
      answer = self.sio.readline()
      print(answer)
      if not answer.endswith("set to {0:05.2f} V\r".format(pValue)):
        print("ERROR: unexpected answer of HM7044: {0}".format(answer))
        return -10
      
    if(pUnit == "A"):
      if float(pValue) > 3 or float(pValue) < 0:
        print("ERROR: Current value higher than allowed maximum (3 A) or smaller than zero")
        return -3 
      self.sio.write(str("SET {0:1.3f} A\r".format(pValue)))
      self.sio.flush()
      answer = self.sio.readline()
      print(answer)
      if not answer.endswith("set to {0:5.3f} A\r".format(pValue)):
        print("ERROR: unexpected answer of HM7044: {0}".format(answer))
        return -10
    return 1
    
  def fuse(self, pBool, pChannelCoupling):
    
    if (len(pChannelCoupling.split(',')) != 4):
      print("Coupling needs four parameters (x,x,x,x)")
      return -2
    if pBool:
      self.sio.write(str("FUSE ON \r"))
    else: 
      self.sio.write(str("FUSE OFF \r"))
    self.sio.flush()
    answer = self.sio.readline()
    print(answer)
    if pBool:
      if not answer.endswith(" fuse on\r"):
        print("ERROR: unexpected answer of HM7044: {0}".format(answer))
        return -10
    else: 
      if not answer.endswith(" fuse off\r"):
        print("ERROR: unexpected answer of HM7044: {0}".format(answer))
        return -10
    
    self.sio.write("FUSE {0}\r".format(pChannelCoupling))
    self.sio.flush()
    answer = self.sio.readline()
    print(answer)
    if not answer == "fuse set to {0}\r".format(pChannelCoupling):
      return -10
    return 1
    
  def read(self):
    
    self.sio.write("READ\r")
    self.sio.flush()
    answer = self.sio.readline()
    print(answer)
    print("READ")
    if "ERROR" in answer:
      print("ERROR found in answer of HM7044: {0}".format(answer))
      return -10
    splitted = answer.split(' ;')
    
    ch1 = HamegChannel()
    ch2 = HamegChannel()
    ch3 = HamegChannel()
    ch4 = HamegChannel()
    
    ch1.Voltage = float(splitted[0].split(' ')[0][:-1])
    ch2.Voltage = float(splitted[0].split(' ')[1][:-1])
    ch3.Voltage = float(splitted[0].split(' ')[2][:-1])
    ch4.Voltage = float(splitted[0].split(' ')[3][:-1])
    ch1.Current = float(splitted[1].split(' ')[0][:-1])
    ch2.Current = float(splitted[1].split(' ')[1][:-1])
    ch3.Current = float(splitted[1].split(' ')[2][:-1])
    ch4.Current = float(splitted[1].split(' ')[3][:-1])
    self.analyseChStatus(splitted[2], ch1)
    self.analyseChStatus(splitted[2][7:], ch2)
    self.analyseChStatus(splitted[2][14:], ch3)
    self.analyseChStatus(splitted[2][21:], ch4)
    
    return 1
  
  def lock(self, boolean):
    
    if boolean:
      self.sio.write("LOCK ON\r")
      self.sio.flush()
      answer = self.sio.readline()
      print(answer)
      if not answer == "keyboard locked\r":
        print("ERROR: unexpected answer of HM7044: {0}".format(answer))
        return -10
    else:
      self.sio.write("LOCK OFF\r")
      self.sio.flush()
      answer = self.sio.readline()
      print(answer)
      if not answer == "keyboard unlocked\r":
        print("ERROR: unexpected answer of HM7044: {0}".format(answer))
        return -10
    
    return 1
  
  def activateChannels(self):
    
    self.sio.write("ON\r")
    self.sio.flush()
    answer = self.sio.readline()
    print(answer)
    if not answer.endswith(" on\r"):
      print("ERROR: unexpected answer of HM7044: {0}".format(answer))
      return -10
    
    return 1
    
  def disableChannel(self):
    
    self.sio.write("OFF\r")
    self.sio.flush()
    answer = self.sio.readline()
    print(answer)
    if not answer.endswith(" off\r"):
      print("ERROR: unexpected answer of HM7044: {0}".format(answer))
      return -10
    
    return 1
  
  def enableOutput(self):
    
    self.sio.write("ENABLE OUTPUT\r")
    self.sio.flush()
    answer = self.sio.readline()
    print(answer)
    if not answer == "output enabled\r":
      print("ERROR: unexpected answer of HM7044: {0}".format(answer))
      return -10
      
    return 1
    
  def disableOutput(self):
    
    self.sio.write("DISABLE OUTPUT\r")
    self.sio.flush()
    answer = self.sio.readline()
    print(answer)
    if not answer == "output disabled\r":
      print("ERROR: unexpected answer of HM7044: {0}".format(answer))
      return -10
    
    return 1
  
    
  def setChannels(self, pChannelList, pVolt=0, pCurr=0):
    
    cVoltMax = 32
    cCurrMax = 3
    cCurrMin = 0.005
    
    cNrChannels = self.select(pChannelList)
    if  cNrChannels < 0:
      print("Not able to set voltage and current in desired channels '{0}'. Please check your input!".format(pChannelList))
      return -1
    if float(pVolt) > 32 or float(pVolt) < 0:
      print("ERROR: Voltage value higher than allowed maximum (32 V) or smaller than minium (10 mV)")
      return -2 
    if float(pCurr) > 3 or float(pCurr) < 0:
      print("ERROR: Current value higher than allowed maximum (3 A) or smaller than zero")
      return -3 
    cReturn = self.set(pVolt, "V")   
    if  cReturn < 0:
      return cReturn
    cReturn = self.set(pCurr, "A")
    if cReturn < 0:
      return cReturn
    cReturn = self.activateChannel()
    if cReturn < 0:
      return cReturn
      
    return 1
    
      
  def analyseChStatus(self, chAnswer, hamegCh):
    print("ChAnswer", chAnswer)
    if str(chAnswer[0:3]) == "OFF":
      hamegCh.Status = False
      hamegCh.Regulation = ""
    elif str(chAnswer[0:2]) == "CV":
      hamegCh.Status = True
      hamegCh.Regulation = "CV"
    elif str(chAnswer[0:2]) == "CC":
      hamegCh.Status = True
      hamegCh.Regulation = "CC"
    if str(chAnswer[4]) == "-":
      hamegCh.Fuse = False
    hamegCh.FuseParameter = int(chAnswer[5])
    
  def printout(self, status, error):
    a = 5
    
  def isint(self, s):
    try:
      int(s)
      return True
    except ValueError:
      return False
  

class HamegChannel:
  
  def __init__(self):
    self.Voltage = 0.0
    self.Current = 0.0
    self.Status = False   #False = output of channel is off
    self.Regulation = "CV"
    self.Fuse = False
    self.FuseParameter = 0
    
  def retVolt(self):
    return self.Voltage
  
  def retCurr(self):
    return self.Current
    
  def retStat(self):
    return self.Status
    
  def retFuse(self):
    return self.Fuse, self.FuseParameter

    
# main loop
if __name__=='__main__':

    # Instanciate Keithley
    k = HamegControl()
    
    k.init()
    k.select("1,3")
    k.set(2,"A")
    k.activateChannels()
    k.enableOutput()
    #k.select("NONE")
    #k.setChannels("1,2", 10, 0.05)
    #k.fuse(False, "1,2,1,4")
    k.read()
    #k.lock(False)
    
    #k.disableChannel()
    #k.enableOutput()
    #k.disableOutput()
  
#Output from read:
# 12.00V 12.00V 12.00V 12.00V ;0.000A 0.000A 0.001A 3.000A ;OFF F1 OFF F2 OFF F3 OFF F4
# 12.00V 12.00V 12.00V 12.00V ;0.000A 0.000A 0.001A 3.000A ;OFF -1 OFF -2 OFF -3 OFF -4
# 12.00V 12.00V 12.00V 12.00V ;0.000A 0.000A 0.000A 0.000A ;OFF -1 OFF -2 CV  -3 CV  -4
# 12.00V 12.00V 09.64V 12.00V ;0.000A 0.000A 0.000A 0.000A ;OFF -1 OFF -2 CV  -3 CV  -4
