import os
import can
import binascii
from datetime import datetime
import time
import os.path
import click

g_TEST_PAYLOAD = {"arbitration_id": 0x1234, "data": [0x01, 0xe9, 0x29, 0x09, 0x52, 0x03, 0xe8, 0x03]}

@click.command()
#@click.option('-c', '--cfg_file', 'cfg_file', default='can_config.yml',
#              help='path to config file to use. Default is can_config.yml')
#@click.option('-l', '--logging_level', 'logging_level', default='DEBUG',
#              help='''set logging severity DEBUG INFO WARNING ERROR CRITICAL
#              Default INFO''')
#@click.option('-L', '--logging_cfg', 'logging_config',
#              help='''Use logging yaml file to set logging configuration''')
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
        result = ecd.decode_id22(g_TEST_PAYLOAD)
        print(result)


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
        self.msg = None



    def decode_id22(self, msg_data, **kwargs):
        print(msg_data)
        #msg = kwargs.get("can_message", None)
        msg = msg_data
        msgdata = msg_data.get("data", None)


        if msg is None:
            print("no CAN message passed")
            return

        #can_id = msg.arbitration_id
        #can_data = msg.data

        print("\n########## First part of CAN message ##########")

        # byte0: error list
        errors = self.check_bits(msgdata[0])
        self.decoded_can_data["error1"] = self.check_errors(errors)

        # byte1: mark state and gear
        byte_split = self.split_bytes(msgdata[1])
        marks = self.check_marks(byte_split["l_byte"])
        self.decoded_can_data["mark"] = marks
        state_gear = self.state_n_gear(byte_split["h_byte"])
        self.decoded_can_data["state"] = state_gear[0]
        self.decoded_can_data["gear"] = state_gear[1]

        #byte2,3 RPM
        rpm_value = self.assemble_bytes(low_byte=msgdata[2], high_byte=msgdata[3])
        self.decoded_can_data["rpm"] = rpm_value
        #print("RPM:", rpm_value)

        #byte4,5 Battery voltage
        battery_voltage = self.assemble_bytes(low_byte=msgdata[4], high_byte=msgdata[5], divide=10)
        self.decoded_can_data["bat_voltage"] = battery_voltage
        #print("Battery voltage:", battery_voltage)
        
        #byte6,7 Battery current
        battery_current = self.assemble_bytes(low_byte=msgdata[6], high_byte=msgdata[7], divide=10)
        self.decoded_can_data["bat_current"] = battery_current
        #print("Battery current:", battery_current)
        
        return self.decoded_can_data


    def decode_id23(self):
        print("\n*********** Second part of CAN message ***********")
        print("Controller temprature: ", msgdata[0])
        print("Motor temprature: ", msgdata[1])
        print("Motor pos", motor_position(msgdata[3]))
        print("Throttle signal: ", msgdata[4])
        print("Bike faults:", check_errors2(msgdata[6]))

        return self.decoded_can_data


    def split_bytes(self, byte_value):
        '''
        Splits a byte inte its higer and lower part
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
        if timestamp is not None:
            print ("CAN timestamp:", datetime.fromtimestamp(timestamp))

        date_time = datetime.now()
        my_date = date_time.strftime("%Y-%m-%d")
        print("RPi date:", my_date)
        my_time = date_time.strftime("%H:%M:%S.%f")
        print("RPi time:", my_time)

    def print_hex(self, msg):
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

    ############### 1022 decode

    def check_errors(self, errors):
        errors_list = []
        error_codes =   [
                        "motor error", "hall error", "throttle error",
                        "controller error", "brake error", "laimp home"
                        ]
        if(len(errors)):
            for x in errors:
                errors_list.append(error_codes[x])
        else:
            print("no errors!")
        return errors_list


    def check_marks(self, mark_byte):
        '''
        checks marks triggered from a byte and returns a list
        of triggered marks
        '''
        if mark_byte:
            mark_list = []
            print("mark_byte:", mark_byte)
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

        state = ['P', 'R', 'N', 'D']
        gears = ['1', '2', '3', 'S']

        s_value = value & 3
        g_value = (value >> 2) & 3
        #print("Bike state: %s\nBike gear: %s" % 
        #    (state[s_value], gears[g_value]))
        return [s_value, g_value]

    ######################## 1023 decode

    def motor_position(self, rotation_byte):
        '''
        Checks triggered hall sensors value and return motor position
        '''
        if(rotation_byte):
            position = ['A', 'B', 'C']
            motor_pos = ""

            hall_trigger_list = self.check_bits(rotation_byte)
            for x in hall_trigger_list:
                    motor_pos += position[x]
            return motor_pos

        else:
            return None

    def check_errors2(self, error2_byte):
        if (error2_byte):
            faults_list = []
            err2 =  [
                    "Over current", "Over voltag", "Under voltage",
                    "Controller overtemp", "Motor overtemp"
                    ]
            errors_list = self.check_bits(error2_byte)
            
            for x in errors_list:
                faults_list.append(err2[x])

            return faults_list
        return None



if __name__=="__main__":
    exit_code = 0
    exit_code = main()
    sys.exit(exit_code)