import os
import can
import binascii
import click
import time
from datetime import datetime
from prettytable import PrettyTable
from collections import defaultdict

g_TEST_PAYLOAD1 = {"arbitration_id": 0x10261022, "data": [0x01, 0xe9, 0x29, 0x09, 0x52, 0x03, 0xe8, 0x03]}
g_TEST_PAYLOAD2 = {"arbitration_id": 0x10261023, "data": [0x1c, 0x23, 0x00, 0x02, 0x32, 0x00, 0x14, 0x00]}

@click.command()
@click.option('-I', '--id', 'arb_id', help='arbitration id of CAN message')
@click.option('-D', '--data', 'can_data', help='data payload of CAN message')
@click.option('-d', '--dry', 'dry_run', is_flag=True, default=False,
              help='input .dbc file for encoding')
@click.option('-o', '--output', 'ofile_path',
              help='set generated file destination. Default ./')


#def main(cfg_file: str, logging_level: str, logging_config:str, dbc_file: str, 
#         dry_run: bool, ofile_path: str) -> int:

def main(arb_id: str, can_data: str, dry_run: bool, ofile_path: str) -> dict:
    ecd = EmControllerDecoder()
    if dry_run:
        result = ecd.decode_id22(g_TEST_PAYLOAD1)
        result = ecd.decode_id23(g_TEST_PAYLOAD2)
        ecd.print_results(result)


class EmControllerDecoder():
    def __init__(self, *args, **kwargs):
        self.can_ids =   {
                    "EM_CAN_ID1": 0x10261022,
                    "EM_CAN_ID2": 0x10261023
        }
        self.can_id_filter = [
                        {"can_id": 0x1026102F, "can_mask":0x1FFFFFF0, "extended": True}
                        ]
        self.decoded_can_data = {}
        self.decoded_can_data2 = {}
        self.id_mismatch_count = defaultdict(int)
        self.run_errors = {"id_match": self.id_mismatch_count}
        self.msg = None
        self.message_states = {"ignore": 0, "first msg": 1, "second msg": 2}
        self.message_order = self.message_states.get("ignore")


    def decode_list(self, can_msg_list, print_msg=True):
        decoded_list = []
        if can_msg_list is None:
            return None

        arb_id = None
        can_data = None
        can_timestamp = None

        for msg in can_msg_list:
            can_decoded_data = None
            can_timestamp = msg.timestamp
            arb_id = msg.arbitration_id
            can_data = msg.data

            if arb_id is not None:
                can_decoded_data = self.id_match(arb_id, can_data, can_timestamp)
                if can_decoded_data is None:
                #if isinstance(can_decoded_data, type(None)):
                #if callable(can_decoded_data):
                    self.run_errors["id_match"][arb_id] += 1
                    continue
                decoded_list.append(can_decoded_data(can_data, arb_id, can_timestamp))

        print("error:", self.run_errors)
        return decoded_list


    def id_match(self, arb_id, data, timestamp=None):
        '''
        Fetch and return appropriate function based on arbitration id
        '''
        print("in id match:", hex(arb_id))
        return {
                0x10261022: self.decode_id22,
                0x10261023: self.decode_id23
                }.get(arb_id, None)


    def decode_id22(self, msg_data, arb_id="id22", timestamp=None, **kwargs):
        #msg = kwargs.get("can_message", None)
        #msg = msg_data
        #msgdata = msg_data.get("data", None)
        msgdata = msg_data


        if msgdata is None:
            print("no CAN message passed")
            return

        #can_id = msg.arbitration_id
        #can_data = msg.data

        print("\n########## First part of CAN message ##########")

        # byte0: error list
        self.decoded_can_data.clear()
        self.decoded_can_data["part1"] = {}

        self.decoded_can_data["part1"]["arb_id"] = arb_id
        self.decoded_can_data["part1"]["time_stamp"] = self.time_function(timestamp)
        self.decoded_can_data["part1"]["error1"] = self.check_errors1(msgdata[0])

        # byte1: mark state and gear
        byte_split = self.split_bytes(msgdata[1])
        marks = self.check_marks(byte_split["l_byte"])
        self.decoded_can_data["part1"]["mark"] = marks
        state_gear = self.state_n_gear(byte_split["h_byte"])
        self.decoded_can_data["part1"]["state"] = state_gear[0]
        self.decoded_can_data["part1"]["gear"] = state_gear[1]

        #byte2,3 RPM
        rpm_value = self.assemble_bytes(low_byte=msgdata[2], high_byte=msgdata[3])
        self.decoded_can_data["part1"]["rpm"] = rpm_value
        #print("RPM:", rpm_value)

        #byte4,5 Battery voltage
        battery_voltage = self.assemble_bytes(low_byte=msgdata[4], high_byte=msgdata[5], divide=10)
        self.decoded_can_data["part1"]["battery_voltage"] = battery_voltage
        #print("Battery voltage:", battery_voltage)
        
        #byte6,7 Battery current
        battery_current = self.assemble_bytes(low_byte=msgdata[6], high_byte=msgdata[7], divide=10)
        self.decoded_can_data["part1"]["battery_current"] = battery_current
        #print("Battery current:", battery_current)
        
        print("dict clear test", self.decoded_can_data)
        return self.decoded_can_data


    def decode_id23(self, msg_data, arb_id="id23", timestamp=None):
        print("\n########## Second part of CAN message ##########")
        msgdata = msg_data

        self.decoded_can_data2 = {}
        self.decoded_can_data["part2"] = {}
        self.decoded_can_data["part2"]["arb_id"] = arb_id
        self.decoded_can_data["part2"]["time_stamp"] = self.time_function(timestamp)
        self.decoded_can_data["part2"]["arb_id"] = 0x10261023
        self.decoded_can_data["part2"]["ctrl_temp"] = msgdata[0]
        self.decoded_can_data["part2"]["motor_temp"] = msgdata[1]
        self.decoded_can_data["part2"]["motor_position"] = self.motor_position(msgdata[3])
        self.decoded_can_data["part2"]["throttle"] = msgdata[4]
        self.decoded_can_data["part2"]["errors2"] = self.check_errors2(msgdata[6])

        return self.decoded_can_data


    def split_bytes(self, byte_value):
        '''
        Splits a byte into its higer and lower part
        0x2A -> [2, A]
        '''

        lower = byte_value & 15
        higher = (byte_value >> 4) & 15
        return {"h_byte":higher, "l_byte": lower}


    def check_bits(self, byte_value):
        '''
        Check each bit state and returns list of positions
        of enabled bits
        '''

        b=1
        trigger_list = []
        for x in range(8):
            if(byte_value&b): trigger_list.append(x)
            b=b<<1
        return trigger_list


    def assemble_bytes(self, high_byte, low_byte, divide=0):
        '''
        Adds a high byte and a low byte to create a
        16-bit word and returns its value
        '''


        if(divide):
            return ((high_byte<<8) + low_byte)/divide
        return (high_byte<<8) + low_byte


    def time_function(self, timestamp = None):
        #Todo add info
        if timestamp is not None:
            return {"datetime": datetime.fromtimestamp(timestamp)}
            #Todo: revise if time function is still needed and if datetime should be split

        date_time = datetime.now()
        my_date = date_time.strftime("%Y-%m-%d")
        print("RPi date:", my_date)
        my_time = date_time.strftime("%H:%M:%S.%f")
        print("RPi time:", my_time)
        return {"date": my_date, "time": my_time}


    ############### 1022 decode

    def check_errors1(self, errors_byte):
        #Todo add info
        errors_list = []
        error_codes =   [
                        "motor error", "hall error", "throttle error",
                        "controller error", "brake error", "limp home"
                        ]

        # Todo add fail detection by anding 0xC0 instead and handle any errors
        print("Byte content", errors_byte)
        errors_byte = errors_byte & 0x3F
        if errors_byte & 0xC0:
            print("Error! invalid data received")
            return ["invalid input", errors_byte]
        errors = self.check_bits(errors_byte)
        if errors:
            for x in errors:
                errors_list.append(error_codes[x])
        else:
            return None
        return errors_list


    def check_marks(self, mark_byte):
        '''
        checks marks triggered from a byte and returns a list
        of triggered marks
        '''
        mark_list = None
        marks_triggered = None

        if mark_byte:
            mark_list = []

            mark_byte = mark_byte & 0x0F #only use the lowest bits
            marks_triggered = self.check_bits(mark_byte)
            mark_codes =    [
                            "lock moto", "brake", "cruise", "side brake"
                            ]
            for x in marks_triggered:
                mark_list.append(mark_codes[x])
        return mark_list


    def state_n_gear(self, value):
        '''
        checks state and gear and return each
        as a char representation
        '''

        #Todo: add check to see that not multiple states and gears are set
        state = ['P', 'R', 'N', 'D']
        gears = ['1', '2', '3', 'S']

        s_value = value & 0x03
        g_value = (value >> 2) & 0x03
        #print("Bike state: %s\nBike gear: %s" % 
        #    (state[s_value], gears[g_value]))
        return [state[s_value], gears[g_value]]

    ######################## 1023 decode

    def motor_position(self, rotation_byte):
        '''
        Checks triggered hall sensors value and return motor position
        '''
        if(rotation_byte):
            position = ['A', 'B', 'C']
            motor_pos = ""

            #TODO: Add fail trigger if all three poles are triggered at the same time
            rotation_byte = rotation_byte & 0x07 # Only look at the first three bits
            hall_trigger_list = self.check_bits(rotation_byte)

            for x in hall_trigger_list:
                    motor_pos += position[x]
            return motor_pos

        else:
            return None

    def check_errors2(self, error2_byte):
        #Todo add info
        if (error2_byte):
            faults_list = []
            err2 =  [
                    "Over current", "Over voltag", "Under voltage",
                    "Controller overtemp", "Motor overtemp"
                    ]

            error2_byte = error2_byte & 0x1F # only use 5 first bits
            errors_list = self.check_bits(error2_byte)
            
            for x in errors_list:
                faults_list.append(err2[x])

            return faults_list
        return None



if __name__=="__main__":
    exit_code = 0
    exit_code = main()
    sys.exit(exit_code)
    