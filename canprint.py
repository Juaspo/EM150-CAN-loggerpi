import os
import can
import binascii
import click
import time
from datetime import datetime
from prettytable import PrettyTable

g_TEST_PAYLOAD1 = {"arbitration_id": 0x10261022, "data": [0x01, 0xe9, 0x29, 0x09, 0x52, 0x03, 0xe8, 0x03]}
g_TEST_PAYLOAD2 = {"arbitration_id": 0x10261023, "data": [0x1c, 0x23, 0x00, 0x02, 0x32, 0x00, 0x14, 0x00]}

@click.command()
@click.option('-I', '--id', 'arb_id', help='arbitration id of CAN message')
@click.option('-D', '--data', 'can_data', help='data payload of CAN message')
@click.option('-d', '--dry', 'dry_run', is_flag=True, default=False,
              help='input .dbc file for encoding')
@click.option('-o', '--output', 'ofile_path', default=None,
              help='set generated file destination. Default ./')


#def main(cfg_file: str, logging_level: str, logging_config:str, dbc_file: str, 
#         dry_run: bool, ofile_path: str) -> int:

def main(arb_id: str, can_data: str, dry_run: bool, ofile_path: str) -> dict:
    ecd = EmControllerDecoder()
    if dry_run:
        result = ecd.decode_id22(g_TEST_PAYLOAD1)
        result = ecd.decode_id23(g_TEST_PAYLOAD2)
        ecd.print_results(result)

class PrintCanMessage():
    def __init__(self, *args, **kwargs):
        pass

    def print_hex(self, msg):
        #Todo add info
        print("in a for loop")
        msg_data=""
        try:
            for x in range(msg):
                #print(binascii.hexlify(bytearray(msgdata[x])).decode('ascii'))
                #print("0", byte_data, sep='x', end=' ', flush=True)
                msg_data +="%0.2X" % msgdata[x] + ' '
        except IndexError as e:
            print("index error, out of bound:", e)

        if msg_data: print("data:", msg_data)


    def print_encoded_can(self, decoded_results):
        tabulate = PrettyTable(["Key", "Value"])
        for key, value in decoded_results.items():
            tabulate.add_row([key, value])

        print(tabulate)

    def print_decoded_can(self, decoded_results):
        part1_table =  [
                        "Can id", "Timestamp", "Errors1", "Mark", "State", "Gear", "RPM",
                        "Battery voltage", "Battery current"
                       ]
        part2_table =  [
                        "Can id", "Timestamp", "Controller temp", "Motor temp",
                        "Motor pos", "Throttle", "Errors2"
                       ]
        unified_table = [
                         "Can id", "Timestamp", "Errors1", "Mark", "State", "Gear", "RPM",
                        "Battery voltage", "Battery current", "Can id", "Timestamp", 
                        "Controller temp", "Motor temp", "Motor pos", "Throttle", "Errors2"
                        ]



        value_row = []
        if decoded_results is None:
            return print("no data")


        print("print dec:", decoded_results)
        for entry in decoded_results:
            for key, value in entry.items():
                try:
                    if entry.get("part1", None) and entry.get("part2", None):
                        tabulate = PrettyTable(unified_table)
                    elif entry.get("part1", None):
                        tabulate = PrettyTable(part1_table)
                    elif entry.get("part2", None):
                        tabulate = PrettyTable(part2_table)
                    else:
                        for key in entry:
                            print ("no parts found:", key)
                        return None
                    value_row.append(value)
                except ValueError as e:
                    print("Cant prnt key")

        print(value_row)
        tabulate.add_row(value_row)

        #print(tabulate)


class WriteLogFile():
    def __init__(self, *args, **kwargs):
        pass

    def write_file(self, can_msg, output_file_path, filename):

        if output_file_path is None:
            output_file_path = "./can_logs/"

        if filename is None:
            filename = "canlog"

    #try:
        output_file_path = os.path.join(output_file_path, filename + '.' + "log")
        os.makedirs(os.path.dirname(output_file_path), exist_ok = True)
        print("File written to file path:", output_file_path)

        f = open(output_file_path, 'w')
        f.write(str(can_msg))
        f.close()

