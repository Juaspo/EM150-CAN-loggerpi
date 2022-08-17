#!/usr/bin/env python3

# Script created to monitor canbus messages from EM150 controller

'''
id = 0x10261022 
data = 01 E9 29 09 52 03 E8 03
Error = motor error
Lock moto = 0
Brake = 1
Cruise = 0
Side brake = 0
PRND = N
Gears = 3(S)
RPM = 2345
Battery = 85.0
Current = 100.0

0x10261023 DLC 8
data = 1C 23 00 02 32 00 14 00
Controller temp = 28
motor temp = 35
Hall = B
throttle = 50
Error2 = Under voltage, Motor over temp
'''




__all__ = []
__version__ = "0.0.1"
__date__ = "2022-08-02"
__author__ = "Junior Asante"
__status__ = "development"


import sys
import click
import os
import can
import threading
import logging
#import utils
import time
from signal import pause
import RPi.GPIO as GPIO


@click.command()
@click.option('-c', '--cfg_file', 'cfg_file', default='can_config.yml',
              help='path to config file to use. Default is can_config.yml')
@click.option('-l', '--logging_level', 'logging_level', default='DEBUG',
              help='''set logging severity DEBUG INFO WARNING ERROR CRITICAL
              Default INFO''')
@click.option('-L', '--logging_cfg', 'logging_config',
              help='''Use logging yaml file to set logging configuration''')
@click.option('-D', '--dbc', 'dbc_file', help='input .dbc file for encoding')
@click.option('-d', '--dry', 'dry_run', is_flag=True, default=False,
              help='input .dbc file for encoding')
@click.option('-o', '--output', 'ofile_path',
              help='set generated file destination. Default ./')


def main(cfg_file: str, logging_level: str, logging_config:str, dbc_file: str, 
         dry_run: bool, ofile_path: str) -> int:
    nop


led_pin = [11, 13, 15]
led_nr = 0

def led_lightup(led_nr):
    GPIO.output(led_pin[led_nr], GPIO.HIGH)
    time.sleep(1)
    GPIO.output(led_pin[led_nr], GPIO.LOW)

def button_callback():
    GPIO.remove_event_detect(16)
    print("Button pressed!")


    periodic_send.toggle_broadcast()
    #led_thread = threading.Thread(target=send_can, args=())
    #led_thread.start()

    GPIO.add_event_detect(16, GPIO.RISING, callback=lambda x: button_callback(), bouncetime=300)

def send_can():
    msg1_id = 0x10261022
    msg2_id = 0x10261023
    msg1_payload = [0x01, 0xe9, 0x29, 0x09, 0x52, 0x03, 0xe8, 0x03]
    msg2_payload = [0x1c, 0x23, 0x00, 0x02, 0x32, 0x00, 0x14, 0x00]

    os.system('sudo ip link set can0 type can bitrate 250000')
    os.system('sudo ifconfig can0 up')

    can0 = can.interface.Bus(channel = 'can0', bustype = 'socketcan')# socketcan_native

    msg1 = can.Message(arbitration_id=msg1_id, data=msg1_payload, is_extended_id=True)    
    msg2 = can.Message(arbitration_id=msg2_id, data=msg2_payload, is_extended_id=True)
    msgd = can.Message(arbitration_id=msgd_id, data=msgd_payload, is_extended_id=True)

    can0.send(msg1)
    print("%s sent", msg1)
    time.sleep(0.05)
    can0.send(msg2)
    print("%s sent", msg2)

class PeriodicSend():
    def __init__(self, *arg, **kwargs):
        self.msg1_id = 0x10261022
        self.msg2_id = 0x10261023
        self.msgd_id = 0x1026105A
        self.msgx_id = 0x12345678
        self.msg1_payload = [0x01, 0xe9, 0x29, 0x09, 0x52, 0x03, 0xe8, 0x03]
        self.msg2_payload = [0x1c, 0x23, 0x00, 0x02, 0x32, 0x00, 0x14, 0x00]
        self.msgd_payload = [0x01, 0x00, 0x00, 0x07, 0x00, 0x00, 0x00, 0x00]
        self.msgx_payload = [0x01, 0x02, 0x03, 0x04, 0xa0, 0xb0, 0xc0, 0xd0]

        self.taskd = None
        self.task = None
        self.task2 = None
        self.taskx = None

        self.msg1 = None
        self.msg2 = None
        self.msgd = None
        self.msgx = None

        self.active_broadcast = False
        self.display_broadcast = False
        self.random_broadcast = False

        self.can_send_setup()

    def can_send_setup(self):
        os.system('sudo ip link set can0 type can bitrate 250000')
        os.system('sudo ifconfig can0 up')

        self.can0 = can.interface.Bus(channel = 'can0', bustype = 'socketcan')# socketcan_native

        self.msg1 = can.Message(arbitration_id=self.msg1_id, data=self.msg1_payload, is_extended_id=True)    
        self.msg2 = can.Message(arbitration_id=self.msg2_id, data=self.msg2_payload, is_extended_id=True)
        self.msgd = can.Message(arbitration_id=self.msgd_id, data=self.msgd_payload, is_extended_id=True)
        self.msgx = can.Message(arbitration_id=self.msgx_id, data=self.msgx_payload, is_extended_id=True)
        print("ip link and intercafe setup done")


    def toggle_random(self):
        if self.random_broadcast:
            self.stop_random_send()
        else:
            self.start_random_send()

    
    def stop_random_send(self):
        self.taskx.stop()
        print("Stopped random CAN send")
        self.random_broadcast = False
        return self.random_broadcast


    def start_random_send(self, period=1):
        self.taskx = self.can0.send_periodic(self.msgx, period)
        if not isinstance(self.taskx, can.ModifiableCyclicTaskABC):
            print("This interface does not seem to support mods")
            self.taskx.stop()
            self.random_broadcast = False
            return

        self.random_broadcast = True
        print("random broadcast started")
        return self.random_broadcast


    def toggle_display(self):
        if self.display_broadcast:
            self.stop_display_send()
        else:
            self.start_display_send()

    
    def stop_display_send(self):
        self.taskd.stop()
        print("Stopped display CAN send")
        self.display_broadcast = False
        return self.display_broadcast


    def start_display_send(self, period=1):
        self.taskd = self.can0.send_periodic(self.msgd, period)
        if not isinstance(self.taskd, can.ModifiableCyclicTaskABC):
            print("This interface does not seem to support mods")
            self.taskd.stop()
            self.display_broadcast = False
            return

        self.display_broadcast = True
        print("Display boradcast started")
        return self.display_broadcast


    def toggle_broadcast(self):
        if self.active_broadcast:
            self.stop_sending()
        else:
            self.start_sending()

    def stop_sending(self):
        self.task.stop()
        self.task2.stop()
        print("Stopped periodic CAN send")
        self.active_broadcast = False
        return self.active_broadcast

    def start_sending(self, period=0.1):
        self.task = self.can0.send_periodic(self.msg1, period)
        self.task2 = self.can0.send_periodic(self.msg2, period)
        if not isinstance(self.task, can.ModifiableCyclicTaskABC):
            print("This interface does not seem to support mods")
            self.task.stop()
            self.task2.stop()
            self.active_broadcast = False
            return

        print("Started periodic CAN send")
        self.active_broadcast = True
        return self.active_broadcast

    def modify_data_task(self, task_nr, data_entry=None):
        if data is not None:
            if task_nr == 1:
                for key, value in data_entry.items():
                    self.msg1.data[key] = value
                self.task.modify_data(self.msg1)

            elif task_nr == 2:
                for key, value in data_entry.items():
                    self.msg2.data[key] = value
                self.task2.modify_data(self.msg2)
            
            print("CAN data modified")

    def exit_cleanup(self):
        os.system('sudo ifconfig can0 down')
        print("CAN link closed")
        
periodic_send = PeriodicSend()

GPIO.setwarnings(False)  # Ignore warnings
GPIO.setmode(GPIO.BOARD)  # Use physical board layout

GPIO.setup(led_pin, GPIO.OUT)  # Set led pin to output
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Set pin 16 to be input with pulldown

GPIO.add_event_detect(16, GPIO.RISING, callback=lambda x: button_callback(), bouncetime=300)  # Setup event on pin 16 rising edge

user_input = None
while user_input != "":
    user_input = input("Press enter to quit\n")  # Run until someone presses enter
    if user_input == "c" or user_input == "t":
        periodic_send.toggle_broadcast()
    elif user_input == "d":
        periodic_send.toggle_display()
    elif user_input == "x":
        periodic_send.toggle_random()
    else:
        print("no code yet")

periodic_send.exit_cleanup()
GPIO.cleanup()  # Clean up
