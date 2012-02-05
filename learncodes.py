#!/usr/bin/python
import serial
import simplejson
ser = serial.Serial('/dev/ttyUSB0', 115200)
mykeys = {}
lastkey = ()
while 1:
  line = ser.readline()
  try:
    p,a,c,n = line.split()
    if (p,a,c) != lastkey:
      #print line[:-1]
      keyname = raw_input("Enter key name for %s, type 'quit' to exit\n"%(line[:-1]))
      if keyname == "quit":
        break
      mykeys["%s_%s_%s"%(p,a[2:],int(c[2:], 16))] = keyname
    lastkey = (p,a,c)
  except:
    pass
keyjson = simplejson.JSONEncoder().encode(mykeys)
with open("keymap.json","w") as mykeytable:
  mykeytable.writelines(keyjson)
print mykeys
ser.close()
