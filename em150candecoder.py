import os
import can
import binascii
import click
import time
import re
from datetime import datetime
from prettytable import PrettyTable
from collections import defaultdict

g_TEST_PAYLOAD1 = {"arbitration_id": 0x10261022, "data": [0x01, 0xe9, 0x29, 0x09, 0x52, 0x03, 0xe8, 0x03]}
g_TEST_PAYLOAD2 = {"arbitration_id": 0x10261023, "data": [0x1c, 0x23, 0x00, 0x02, 0x32, 0x00, 0x14, 0x00]}

@click.command()
@click.option('-I', '--id', 'arb_id', help='arbitration id of CAN message')
@click.option('-D', '--data', 'can_data', help='data payload of CAN message')
@click.option('-d', '--dry', 'dry_run', is_flag=True, default=False,
              help='test function of decoder without providing CAN data')
@click.option('-i', '--input', 'ifile_path',
              help='input CAN log file for decoding')
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


class CanStates():
    '''
    State class used to determine current state of logger.
    '''

    def __init__(self, *args, **kwargs):
        self.current_state = 0
        self.states = {"reset":0, "part1":1, "part2":2}

    def reset_state(self):
        self.current_state = 0
    def set_part1(self):
        self.current_state = 1
    def set_part2(self):
        self.current_state = 2
    def get_state(self):
        return self.current_state


class EmControllerDecoder():
    def __init__(self, *args, **kwargs):
        self.can_ids = {
                        "EM_CAN_ID1": 0x10261022,
                        "EM_CAN_ID2": 0x10261023
                        }
        self.can_id_filter = [
                        {"can_id": 0x1026102F, "can_mask":0x1FFFFFF0, "extended": True}
                        ]
        self.decoded_can_data = {}
        self.file_timestamp = None
        #self.id_mismatch_count = defaultdict(int)
        self.run_errors = {"id_match": defaultdict(int)}
        self.fails = {"missing part":'-', "batt current":'-', "hall data":'-'}
        self.message_states = {"ignore": 0, "first msg": 1, "second msg": 2}
        self.message_order = self.message_states.get("ignore")
        self.msg_count_dict = {
                                "total": 0, "ctrl1": 0, "ctrl2": 0, 
                                "display": 0, "other": 0
                                }
        self.meta_data = {}
        self.msg_pack = {"meta_data": {}, "data": []}

        self.can_state = CanStates()
        self.combine_part1 = {}
        self.combined_can = {}
        self.combined_can_default = {
                            "Date":'-', "Time":'-', "Errors":'-', "State":'-',
                            "PRND":'-', "Gear":'-', "RPM":'-', "Batt voltage":'-',
                            "Batt current":'-', "Timestamp2":'-',
                            "Controller temp":'-', "Motor temp":'-',
                            "Hall position":'-', "Throttle %":'-', "Faults":'-',
                            "Fails":'-'
                            }


    def get_csv_header(self):
        '''
        Get CSV header
        returns: The header for csv file
        '''

        header_list = []
        for keys in self.combined_can_default:
            header_list.append(keys)

        return header_list


    def new_session(self):
        '''
        Clears counters and initiate and return current time stamp
        returns: current timestamp
        '''

        self.clear_counters()
        self.set_filename_timestamp()
        return self.get_filename_timestamp()


    def set_filename_timestamp(self):
        '''
        Set filename timestamp
        '''

        self.msg_pack["meta_data"]["file_timestamp"] = self.get_time(file_time=True)


    def get_filename_timestamp(self):
        '''
        Get filename timestamp
        returns: filename timestamp
        '''
        return self.msg_pack["meta_data"].get("file_timestamp", None)


    def get_counters(self):
        '''
        Get current counters
        returns: Current counter [dict]
        '''
        return self.msg_count_dict


    def clear_counters(self, counter=["total", "ctrl1", "ctrl2", "display", "other"]):
        for cntr in counter:
            self.msg_count_dict[cntr] = 0

        #print("counters clear:", self.msg_count_dict)


    def combine_decode_entry(self, can_data, can_id, **kwargs):
        '''
        Used to run decoder and assemle part 1 and 2 of controller
        data. Error checking for missing parts will be run as well.

        returns: decoded can data [dict]
        '''

        timestamp = kwargs.get("timestamp", None)
        hit = kwargs.get("hit", False)
        combine_part = None
        if self.can_state.get_state() == self.can_state.states.get("reset"):
            self.combined_can.clear()
            self.combined_can = dict(self.combined_can_default)
            self.can_state.set_part1()


        can_decoded_data = None

        if can_id is not None:
            self.msg_count_dict["total"] += 1

        if can_data is None:
            print("can data is None", can_id)
            self.msg_count_dict["other"] += 1
            self.run_errors["id_match"][can_id] += 1
            return None

        if self.can_state.get_state() == self.can_state.states.get("part2"):
            if can_id == 0x10261022:
                print("missing part2")
                self.fails["part miss"] = "2"
                self.can_state.set_part1()


        if can_id == 0x10261022 or can_id == 0x10261023:
            print ("processing data")
            x = self.id_match(can_id)
            decoded_data = x(can_data, can_id, timestamp, hit)
            #print("decoded data:", decoded_data)

            for key in self.combined_can.keys():
                value = decoded_data.get(key, None)
                if value is not None:
                    self.combined_can[key] = value

            #print("current state:", self.can_state.get_state())
            if self.can_state.get_state() == self.can_state.states.get("part1"):
                if can_id == 0x10261023:
                    self.fails["part miss"] = "1"
                    self.combined_can["Fails"] = self.fails
                    return self.combined_can

                self.can_state.set_part2()
                return None

            elif self.can_state.get_state() == self.can_state.states.get("part2"):
                if can_id == 0x10261022:
                    self.fails["part miss"] = "2"
                    self.combined_can["Fails"] = self.fails
                    return None
                elif can_id == 0x10261023:
                    self.can_state.reset_state()
                    return self.combined_can

        elif can_id == 0x1026105a:
            self.msg_count_dict["display"] += 1
            #print("diaplay msg")
            return None

        else:
            self.msg_count_dict["other"] += 1
            #print("other msg")
            return None

        return None


    def decode_entry(self, can_data, can_id, **kwargs):
        '''
        Used to decode single entries. No combining of parts or
        check for missing parts will be done

        returns: decoded CAN data [dict]
        '''

        timestamp = kwargs.get("timestamp", None)
        hit = kwargs.get("hit", False)

        can_decoded_data = None

        self.msg_count_dict["total"] += 1
        can_decoded_data = self.id_match(can_id)

        if can_decoded_data is None:
            self.msg_count_dict["other"] += 1
            self.run_errors["id_match"][can_id] += 1
            return None

        return can_decoded_data(can_data, can_id, timestamp, hit)


    def decode_file(self, file_path):
        '''
        Used for decoding of files. No combining of parts
        or missing parts check will be performed

        returns: decoded CAN data [dict]
        '''


        can_decoded_data = None
        decoded_list = []

        self.get_filename_timestamp()

        print("filepath:", file_path)
        with open(file_path) as infile:
            for line in infile:
                can_data = self.parse_text(line)

                if can_data is not None:
                    x = self.decode_entry(can_data[1], can_data[0], **{'timestamp':can_data[2], 'hit':True})
                    if x is not None:
                        decoded_list.append(x)


        self.msg_pack["data"] = decoded_list
        self.msg_pack["meta_data"].update(self.msg_count_dict)
        print("error:", self.run_errors)
        return self.msg_pack


    def decode_file_line(self, line):
        '''
        Decoding of file data with combined part 1 and 2.
        Missing parts check will be performed

        returns: decoded CAN data [dict]
        '''


        can_data = self.parse_text(line)

        if can_data is not None:
            #print("can_data file line:", can_data)
            x = self.combine_decode_entry(can_data[1], can_data[0], **{'timestamp':can_data[2], 'hit':True})
            if x is not None:
                return x


    def decode_list(self, can_msg_list, print_msg=True):
        '''
        Decoding of CAN list data. No combining of parts or
        missing part checks will be done

        returns: decoded CAN data [dict]
        '''

        decoded_list = []
        if can_msg_list is None:
            return None

        for msg in can_msg_list:
            arb_id = msg.arbitration_id
            can_data = msg.data
            extras = {"timestamp": msg.timestamp, "hit": True}

            if arb_id is not None:
                x = self.decode_entry(can_data, arb_id, **extras)
                if x is not None:
                    decoded_list.append(x)

        self.msg_pack["data"] = decoded_list
        self.msg_pack["meta_data"].update(self.msg_count_dict)
        return self.msg_pack


    def parse_text(self, line: str):
        '''
        Parse encoded log to find apprpritate CAN data.
        This includes CAN id as well as CAN data

        returns: found CAN data [list]
        '''

        #hex_pattern = re.compile(r"\scan?[0-9]\s+([0-9a-fA-F]+).{8}(([0-9a-fA-F]{2}\s){8})")
        hex_pattern = re.compile(r"([0-9]{10}\.[0-9]{6})\s.+\s([0-9a-fA-F]{8})\s[0-9]\s((([0-9a-fA-F]{1,2})\s?){8})")
        
        can_data = re.search(hex_pattern, line)
        
        if can_data:
            can_time = float(can_data.group(1))
            can_id = int(can_data.group(2), 16)
            data = can_data.group(3)
            data = data.strip().split(' ')

            data_list = []
            for y in data: data_list.append(int(y, 16))

            data = bytearray()
            data.extend(data_list)


            return [can_id, data, can_time]
        else:
            return None


    def id_match(self, arb_id):
        '''
        Fetch and return appropriate function based on arbitration id

        returns: Appropriate functions for given CAN id [func]
        '''

        return {
                0x1026105A: self.decade_id5A,
                0x10261022: self.decode_id22,
                0x10261023: self.decode_id23
                }.get(arb_id, None)


    def decade_id5A(self, msg_data, arb_id="id5A", timestamp=None, hit=False):
        '''
        Increment display CAN count. Used for when match on display CAN id detected
        '''

        if  hit:
            self.msg_count_dict["display"] += 1


    def decode_id22(self, msg_data, arb_id="id22", timestamp=None, hit=False):
        '''
        Decoding process for EM controller CAN part1 (id22)

        returns: Decoded part1 CAN data [dict]
        '''

        if hit:
            self.msg_count_dict["ctrl1"] += 1

        if msg_data is None:
            print("no CAN message passed")
            return

        # byte0: error list
        self.decoded_can_data.clear()
        can_dict = {}

        # arbitration id, timestamp and error1 check
        can_dict["Arbitration id"] = arb_id
        can_dict.update(self.get_time(timestamp))
        #can_dict["Timestamp1"] = self.get_time(timestamp)
        can_dict["Errors"] = self.check_errors1(msg_data[0])

        # byte1: mark state and gear
        byte_split = self.split_bytes(msg_data[1])
        can_dict["State"] = self.check_marks(byte_split["l_byte"])
        state_gear = self.prnd_n_gear(byte_split["h_byte"])
        can_dict["PRND"] = state_gear[0]
        can_dict["Gear"] = state_gear[1]

        # byte2,3 RPM
        rpm_value = self.assemble_bytes(low_byte=msg_data[2], high_byte=msg_data[3])
        can_dict["RPM"] = rpm_value

        # byte4,5 Battery voltage
        battery_voltage = self.assemble_bytes(low_byte=msg_data[4], high_byte=msg_data[5], divide=10)
        can_dict["Batt voltage"] = battery_voltage
        
        # byte6,7 Battery current
        battery_current = self.assemble_bytes(low_byte=msg_data[6], high_byte=msg_data[7], divide=10)
        if battery_current == 0xFF: 
            battery_current = 0

        can_dict["Batt current"] = battery_current

        return can_dict


    def decode_id23(self, msg_data, arb_id="id23", timestamp=None, hit=False):
        '''
        Decoding process for EM controller CAN part2 (id23)

        returns: Decoded part2 CAN data [dict]
        '''

        if hit:
            self.msg_count_dict["ctrl2"] += 1

        can_dict = {}
        can_dict["Arbitration id"] = arb_id
        can_dict["Timestamp2"] = self.get_time(timestamp)
        can_dict["Controller temp"] = msg_data[0]
        can_dict["Motor temp"] = msg_data[1]
        can_dict["Hall position"] = self.motor_position(msg_data[3])
        can_dict["Throttle %"] = msg_data[4]
        can_dict["Faults"] = self.check_errors2(msg_data[6])

        return can_dict


    def split_bytes(self, byte_value):
        '''
        Splits a byte into its higer and lower part
        0x2A -> [2, A]

        returns: list of high low byte [list]
        '''

        lower = byte_value & 15
        higher = (byte_value >> 4) & 15
        return {"h_byte":higher, "l_byte": lower}


    def check_bits(self, byte_value):
        '''
        Check each bit state and returns list of positions
        of enabled bits

        returns: list of high bit positions [list]
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
        If divide is provided the result will be divided with
        provided value

        returns: value of combined high low byte [int]
        '''


        if(divide):
            return ((high_byte<<8) + low_byte)/divide
        return (high_byte<<8) + low_byte


    def get_time(self, timestamp = None, file_time = False):
        '''
        Get various time stamps. If Unix time provided then return
        converted time. If not return current system time.
        If file time enabled format time for file name.

        returns: time information [str]
        '''


        if timestamp is not None:
            date_time = datetime.fromtimestamp(timestamp)
        else:
            date_time = datetime.now()

        if file_time:
            return date_time.strftime("%y%m%d_%H%M%S")

        my_date = date_time.strftime("%Y-%m-%d")
        my_time = date_time.strftime("%H:%M:%S.%f")
        return {"Date": my_date, "Time": my_time}


    ############### 1022 decode

    def check_errors1(self, errors_byte):
        '''
        Performs error1 check on byte to see if any errors
        are triggered from controller dide.

        returns: triggered errors [list]
        '''

        errors_list = []
        error_codes =   [
                        "motor error", "hall error", "throttle error",
                        "controller error", "brake error", "limp home"
                        ]

        # Todo add fail detection by anding 0xC0 instead and handle any errors

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

        returns: states of motorbike [list]
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


    def prnd_n_gear(self, value):
        '''
        checks state and gear and return each
        as a char representation
        '''

        #Todo: add check to see that not multiple states and gears are set
        state = ['P', 'R', 'N', 'D']
        gears = ['1', '2', '3', 'S']

        s_value = value & 0x03
        g_value = (value >> 2) & 0x03

        return [state[s_value], gears[g_value]]

    ######################## 1023 decode

    def motor_position(self, rotation_byte):
        '''
        Checks triggered hall sensors value and return motor position

        returns: motor hall position [list]
        '''
        if(rotation_byte):
            position = ['A', 'B', 'C']
            motor_pos = ""

            rotation_byte = rotation_byte & 0x07 # Only look at the first three bits
            if rotation_byte == 0x07 or rotation_byte == 0x00:
                fails["hall data"] = "hall error: " + rotation_byte

            hall_trigger_list = self.check_bits(rotation_byte)


            for x in hall_trigger_list:
                    motor_pos += position[x]
            return motor_pos

        else:
            return None

    def check_errors2(self, error2_byte):
        '''
        Perform fault checks on povided value to see
        if any fualts are reported from controller.

        returns: list of triggered faults [list]
        '''

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
