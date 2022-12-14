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
    #my_receiver = CanBusListener()
    #my_receiver.simple_listener()

    my_decoder = em150candecoder.EmControllerDecoder()
    my_can_print = canprint.PrintCanMessage()
    my_can_write = canprint.WriteLogFile()

    encoded_messages = None
    filename = ""
    extension = ""
    log_file = ""
    source_filepath = ""
    destination_filepath = ""
    data_source = "./can_data"
    data_result = "./can_result"


    user_input = None
    while user_input != "":
        user_input = input("Press enter to quit\n")  # Run until someone presses enter
        if user_input == "r":
            filename = my_decoder.new_session()

            print("filename:", filename)
            #encoded_messages = my_receiver.get_buffered_messages()
            decoded_messages = my_decoder.decode_list(encoded_messages)
            #print("Decoded messages:", decoded_messages)
            #my_can_print.print_decoded_can(decoded_messages)

            #filename = my_decoder.get_filename_timestamp()
            my_can_write.write_file(decoded_messages, None, filename)

        elif user_input == "e":
            #my_receiver.exit_program()
            pass

        elif user_input == 'f':
            filename = my_decoder.new_session()
            filename = "test"
            decoded_messages = my_decoder.decode_file("./test_code/190822_roam_lite.log")
            my_can_write.write_file(decoded_messages, None, filename)

        elif user_input == 'c':
            my_decoder.clear_counters()
            print("Counters cleared!")

        elif user_input == 'v':
            print("decoding CAN data...")
            my_decoder.new_session()

            for log_file in os.listdir(data_source):
                print("----------------------------")
                print("log_file:", log_file)
                filename = os.path.splitext(log_file)[0]    
                extension = os.path.splitext(filename)[1]
                source_filepath = os.path.join(data_source, log_file)
                destination_filepath = os.path.join(data_result, log_file)


                # filename = "test2"
                ifile_path = source_filepath
                print("input filepath:", ifile_path)

                my_file = my_can_write.create_csv_file(data_result, filename)
                my_headers = my_decoder.get_csv_header()
                my_can_write.write_csv_row(my_file, my_headers)

                with open(ifile_path) as infile:
                    for line in infile:
                        can_data = my_decoder.parse_text(line)
                        if can_data is not None:
                            decoded_messages = my_decoder.combine_decode_entry(can_data[1], can_data[0], **{'timestamp':can_data[2], 'hit':True})
                            #print("result:", decoded_messages)

                        if decoded_messages is not None:
                            my_can_write.write_csv_dict(my_file, [decoded_messages], my_headers)


                my_counter = my_decoder.get_counters()
                my_counter_str = my_can_write.write_dict_to_file(my_file, my_counter, "\n")
                print(my_counter_str)

                my_can_write.write_to_file(my_file, my_counter_str)
                my_can_write.close_file(my_file)

                os.rename(source_filepath, destination_filepath)
                print(f"moved {source_filepath} to {destination_filepath}")

                my_decoder.clear_counters()



    #my_receiver.stop_listener()
    #my_receiver.exit_program()
    #time.sleep(1)


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
