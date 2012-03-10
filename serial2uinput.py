#!/usr/bin/python

# Alexander Grothe 2011 - 2012
#
# This script requires python-uinput V 0.6.1. or higher. Additional required packages are libudev0 and libudev-dev.
#
### Fetch the code for python-uinput from git: ###
#
# git clone git://github.com/tuomasjjrasanen/python-uinput.git
# cd python-uinput
# git clone git://github.com/tuomasjjrasanen/libsuinput.git
# sudo python setup.py install
#
###
#
# This script must be run as superuser or with sufficent rights to create an uinput device and exspects a lircd socket using pid from /var/run/lirc/lircd.pid under /var/run/lirc/lircd.<pid of lircd> if none is given by --lircd-socket /PATH/TO/LIRCD_SOCKET
# lircd must not be startet with --uinput, but may be started with --release="_up" to prevent ghosting events if necessary.

import simplejson
import serial
import syslog
import string
import socket
import time
import sys
import uinput
import datetime
from optparse import OptionParser

class Lirc2uinput:
    """Sends keystrokes to a virtual uinput device after applying a repeat-filter"""
    def __init__(self, uinput_name="lircd", options=None):
        self.lastkey = None
        self.wait_repeats = options.wait_repeats
        self.max_gap = options.max_gap
        self.min_gap = options.min_gap
        self.acceleration = options.acceleration
        self.serial_socket = options.serial_socket
        self.gap_delta = (self.max_gap - self.min_gap)*self.acceleration
        self.current_gap = self.max_gap
        self.repeat_num = 0
        self.timestamp = datetime.datetime.now()
        # add all defined KEY_.* to supported key events
        self.events = []
        for element in dir(uinput):
          if element.startswith("KEY_"):
            self.events.append(eval("uinput.%s"%element))
            #print "uinput.%s"%element
        # create uinput device
        self.device = uinput.Device(self.events, uinput_name)
        self.specialkeys = [(1, 114),(1, 115)] # KEY_VOLUMEDOWN and KEY_VOLUMEUP - a "real" repeat behaviour is used.


    def get_gap(self,repeat_num):
        if self.current_gap > self.min_gap:
            self.current_gap = self.current_gap - self.gap_delta
        else:
            #print "minimum gap reached"
            pass
        return self.current_gap
    
    def send_key(self,key):
        keycmd = eval('uinput.%s'%(key.replace("_up","")))
        #print keycmd
        now = datetime.datetime.now()
        if key.endswith("_up"):
            print "released %s"%(key[:-3])
            self.device.emit(keycmd, 0)
            self.repeat_num = 0
            self.timestamp = datetime.datetime.now()
            self.current_gap = self.max_gap
        elif self.lastkey == keycmd:
            if (now - self.timestamp).microseconds < self.current_gap:
                #print "Passing keypress... too early"#"repeated %s %s times"%(key,self.repeat)
                pass     
            else:
                #print "Repeated keypress"
                if self.repeat_num >= self.wait_repeats:
                    self.current_gap = self.get_gap(self.repeat_num)
                else:
                    pass
                self.keypress(keycmd, 2)
                self.timestamp = datetime.datetime.now()
                self.repeat_num += 1

        else:
            #print "first keypress"
            self.keypress(keycmd, 1)
            self.timestamp = datetime.datetime.now()
            self.current_gap = self.max_gap
            self.repeat_num = 0

        self.lastkey=keycmd
        
    def keypress(self, key, value):
        if key in self.specialkeys:
            self.device.emit(key, value)
            #self.current_gap = 
        else:
            self.device.emit(key, 1)
            self.device.emit(key, 0)


class main:
    """Listens to LIRC's domain socket and calls a method each time an
    IR command is received."""
    def __init__(self):
        parser = Options()
        self.options = parser.get_opts()
        self.syslog_init()
        # use /dev/ttyUSB0 as socket
        self.socket_path = self.options.serial_socket
        with open(self.options.keymap,'r') as keymapfile:
            self.keymap = simplejson.JSONDecoder().decode(keymapfile.read())
            syslog.syslog("successfully loaded keymap")
            #syslog.syslog(self.keymap)
        self.uinputdev = Lirc2uinput(options=self.options)
        self.listen2socket()
        

    def listen2socket(self):
        #self.sock.connect(self.socket_path)        
        ser = serial.Serial('/dev/ttyUSB0', 115200)
        try:  
          while 1:
            line = ser.readline()
            #print line[:-1]
            #ser.close()
            p = 0
            a = 0
            c = 0
            n = 0
            try:
              p,a,c,n = line.split()
            except:
              #print line[:-1], p,a,c,n
              pass
            try:
              #print "%s_%s_%s"%(p,a[2:],int(c[2:], 16))
              cmd = self.keymap["%s_%s_%s"%(p,a[2:],(int(c[2:], 16)))]
              #print cmd
              self.uinputdev.send_key(cmd)
            except:
              #print "no command found"
              pass
        except:
          pass
        finally:
          ser.close()
            
    def syslog_init(self):
        syslog.syslog('Started serial2uinput.py with these options:')
        syslog.syslog('wait_repeats = %s'%(self.options.wait_repeats))
        syslog.syslog('max_gap = %s'%(self.options.max_gap))
        syslog.syslog('min_gap = %s'%(self.options.min_gap))
        syslog.syslog('acceleration = %s'%(self.options.acceleration))


class Options:
    def __init__(self):
        self.parser = OptionParser()
        self.parser.add_option("-l", "--min-gap", dest="min_gap", default=150000, type="int",
                  help="set minimum gap between repeated keystrokes (default 150000)", metavar="MIN_GAP")
        self.parser.add_option("-u", "--max-gap", dest="max_gap", default=300000, type="int",
                  help="set maximum gap between repeated keystrokes (default 300000)", metavar="MAX_GAP")
        self.parser.add_option("-r", "--min-repeats", dest="wait_repeats", default=2, type="int",
                  help="number of repeats before using accelerated keypresses (default = 2)", metavar="WAIT_REPEATS")
        self.parser.add_option("-a", "--acceleration", dest="acceleration", default=0.25, type="float",
                  help="acceleration to get from MAX_GAP to MIN_GAP. default value of 0.25 equals 4 repeated keystrokes to reach maximum speed",
                    metavar="ACCELERATION")
        self.parser.add_option("-s", "--serial-socket", dest="serial_socket", default=None,
                  help="choose lircd socket to listen on", metavar="SERIAL_SOCKET")
        self.parser.add_option("-k", "--keymap", dest="keymap", default="keymap.json",
                  help="choose keymap to use", metavar="KEYMAP")
    def get_opts(self):
        (options, args) = self.parser.parse_args()
        return options


if __name__ == "__main__":
    vlirc = main()



