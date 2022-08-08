#!/usr/bin/env python3

# Script created to monitor canbus messages from EM150 controller

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
    #GPIO.remove_event_detect(16)
    global led_nr
    print("Button pressed!")
    print("Led nr: ", led_nr)
    
    led_thread = threading.Thread(target=led_lightup, args=(led_nr,))
    led_thread.start()
    send_can()

    led_nr = led_nr + 1
    if led_nr >= 3:
        led_nr = 0

    #GPIO.add_event_detect(16, GPIO.RISING, callback=lambda x: button_callback(), bouncetime=300)

def send_can():
    os.system('sudo ip link set can0 type can bitrate 250000')
    os.system('sudo ifconfig can0 up')

    can0 = can.interface.Bus(channel = 'can0', bustype = 'socketcan')# socketcan_native

    msg = can.Message(arbitration_id=0x123, data=[0, 1, 2, 3, 4, 5, 6, 7], is_extended_id=False)

    can0.send(msg)

    #for n in range(5):
    #    can0.send(msg)
    #    time.sleep(1)

    os.system('sudo ifconfig can0 down')
    


GPIO.setwarnings(False)  # Ignore warnings
GPIO.setmode(GPIO.BOARD)  # Use physical board layout

GPIO.setup(led_pin, GPIO.OUT)  # Set led pin to output
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Set pin 16 to be input with pulldown

GPIO.add_event_detect(16, GPIO.RISING, callback=lambda x: button_callback(), bouncetime=300)  # Setup event on pin 16 rising edge

message = input("Press enter to quit\n\n")  # Run until someone presses enter

GPIO.cleanup()  # Clean up