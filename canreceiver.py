import os
import can
import binascii
import click
import time
from datetime import datetime
from prettytable import PrettyTable

import em150candecoder
import canprint

g_TEST_PAYLOAD1 = {"arbitration_id": 0x10261022, "data": [0x01, 0xe9, 0x29, 0x09, 0x52, 0x03, 0xe8, 0x03]}
g_TEST_PAYLOAD2 = {"arbitration_id": 0x10261023, "data": [0x1c, 0x23, 0x00, 0x02, 0x32, 0x00, 0x14, 0x00]}

@click.command()
@click.option('-I', '--id', 'arb_id', help='arbitration id of CAN message')
@click.option('-D', '--data', 'can_data', help='data payload of CAN message')
@click.option('-d', '--dry', 'dry_run', is_flag=True, default=False,
              help='input .dbc file for encoding')
@click.option('-o', '--output', 'ofile_path',
              help='set generated file destination. Default ./')


def main(arb_id: str, can_data: str, dry_run: bool, ofile_path: str) -> dict:
    my_receiver = CanBusListener()
    my_receiver.simple_listener()

    my_decoder = em150candecoder.EmControllerDecoder()
    my_can_print = canprint.PrintCanMessage()
    my_can_write = canprint.WriteCanMessage()

    encoded_messages = None

    user_input = None
    while user_input != "":
        user_input = input("Press enter to quit\n")  # Run until someone presses enter
        if user_input == "r":
            encoded_messages = my_receiver.get_buffered_messages()
            decoded_messages = my_decoder.decode_list(encoded_messages)
            print("Decoded messages:", decoded_messages)
            #my_can_print.print_decoded_can(decoded_messages)

            filename = decoded_messages["meta_data"]["file_timestamp"]
            my_can_write.write_file(decoded_messages, None, filename)

        elif user_input == "e":
            my_receiver.exit_program()



    my_receiver.stop_listener()
    my_receiver.exit_program()
    #time.sleep(1)

'''
# TODO: this function is not needed and should be removed
    
def convert_msg(messages):

    message_pack_dict = None
    message_pack_list = None

    if messages is not None:
        message_pack_dict = {}
        message_pack_list = []
        for x in range(len(messages)):
            print(x)
            message_pack_dict["can_time"] = messages[x].timestamp
            message_pack_dict["cen_id"] = messages[x].arbitration_id
            message_pack_dict["cen_data"] = messages[x].data
            message_pack_list.append(message_pack_dict)

        return message_pack_list
'''


class CanBusListener():
    def __init__(self, *args, **kwargs):
        self.listener = None
        self.can_bus = None
        self.can0 = None

    def simple_listener(self):
        os.system('sudo ip link set can0 type can bitrate 250000')
        os.system('sudo ifconfig can0 up')

        self.can0 = can.ThreadSafeBus(channel='can0', interface='socketcan')
        self.listener = can.BufferedReader()
        self.notifier = can.Notifier(self.can0, [self.listener])
        #msg = self.can0.recv(5.0)


    def stop_listener(self):
        try:
            self.listener.stop()
        except:
            print("Error occured")
        print("Stopped listener")

    def exit_program(self):
        try:
            os.system('sudo ifconfig can0 down')
        except:
            print("Error on exit close down")

    def get_can_message(self):
        return self.listener.get_message()

    def get_buffered_messages(self):
        message = None
        message_list = []
        while True:
            message = self.get_can_message()
            if message is None:
                break
            message_list.append(message)
        return message_list


if __name__=="__main__":
    exit_code = 0
    exit_code = main()

    sys.exit(exit_code)
