import os
import can
import binascii
from datetime import datetime
import time


############ bit/byte manupilations
can_ids =   {
            "EM_CAN_ID1": 0x10261022,
            "EM_CAN_ID2": 0x10261023
}

def split_bytes(byte_value):
    '''
    Splits a byte inte its higer and lower part
    0x2A -> [2, A]
    '''

    lower = byte_value & 15
    higher = (byte_value >> 4) & 15
    return {"h_byte":higher, "l_byte": lower}


def check_bits(byte_value):
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


def assemble_bytes(high_byte, low_byte, divide=0):
    '''
    Adds a high byte and a low byte to create a
    16-bit word and returns its value
    '''


    if(divide):
        return ((high_byte<<8) + low_byte)/divide
    return (high_byte<<8) + low_byte


def time_function(timestamp = None):
    if timestamp is not None:
        print ("CAN timestamp:", datetime.fromtimestamp(timestamp))

    date_time = datetime.now()
    my_date = date_time.strftime("%Y-%m-%d")
    print("RPi date:", my_date)
    my_time = date_time.strftime("%H:%M:%S.%f")
    print("RPi time:", my_time)

def print_hex(msg):
    print("in a for loop")
    msg_data=""
    try:
        for x in range(msg):
            #print(binascii.hexlify(bytearray(msg.data[x])).decode('ascii'))
            #print("0", byte_data, sep='x', end=' ', flush=True)
            msg_data +="%0.2X" % msg.data[x] + ' '
    except IndexError as e:
        print("index error, out of bound:", e)

    if msg_data: print("data:", msg_data)

############### 1022 decode

def check_errors(errors):
    error_codes =   [
                    "motor error", "hall error", "throttle error",
                    "controller error", "brake error", "laimp home"
                    ]
    if(len(errors)):
        for x in errors:
            print(error_codes[x])
    else:
        print("no errors!")


def check_marks(mark_byte):
    '''
    checks marks triggered from a byte and returns a list
    of triggered marks
    '''
    if mark_byte:
        mark_list = []
        print("mark_byte:", mark_byte)
        marks_triggered = check_bits(mark_byte)
        mark_codes =    [
                        "lock moto", "brake", "cruise", "side brake"
                        ]
        for x in marks_triggered:
            mark_list.append(mark_codes[x])
    return mark_list


def state_n_gear(value):
    '''
    checks state and gear and return each
    as a char representation
    '''

    state = ['P', 'R', 'N', 'D']
    gears = ['1', '2', '3', 'S']

    s_value = value & 3
    g_value = (value >> 2) & 3
    print("Bike state: %s\nBike gear: %s" % 
        (state[s_value], gears[g_value]))
    return [s_value, g_value]

######################## 1023 decode

def motor_position(rotation_byte):
    '''
    Checks triggered hall sensors value and return motor position
    '''
    if(rotation_byte):
        position = ['A', 'B', 'C']
        motor_pos = ""

        hall_trigger_list = check_bits(rotation_byte)
        for x in hall_trigger_list:
                motor_pos += position[x]
        return motor_pos

    else:
        return None

def check_errors2(error2_byte):
    if (error2_byte):
        faults_list = []
        err2 =  [
                "Over current", "Over voltag", "Under voltage",
                "Controller overtemp", "Motor overtemp"
                ]
        errors_list = check_bits(error2_byte)
        
        for x in errors_list:
            faults_list.append(err2[x])

        return faults_list
    return None

os.system('sudo ip link set can0 type can bitrate 250000')
os.system('sudo ifconfig can0 up')
can_id_filter = [
                {"can_id": 0x1026102F, "can_mask":0x1FFFFFF0, "extended": True}
                ]
#can0 = can.interface.Bus(channel='can0', bustype='socketcan', can_filters=can_id_filter)# socketcan_native
#can0 = can.interface.Bus(channel='can0', bustype='socketcan') # no filters
can0 = can.ThreadSafeBus(channel='can0', interface='socketcan')

msg = can0.recv(10.0)



if msg is None:
    print('Timeout occurred, no message.')
else:

    print ("Can data:", msg)
    time_function(msg.timestamp)

    can_id = msg.arbitration_id
    can_data = msg.data

    print("id", can_id)
    ###################### Run CAN process

    if(can_id == can_ids.get("EM_CAN_ID1")):
        print("\n########## First part of CAN message ##########")

        #print(f"time: {msg.timestamp}\narb id: {hex(msg.arbitration_id)}\ndlc: {msg.dlc}\ndata {binascii.hexlify(msg.data)}")

        
        errors = check_bits(msg.data[0])
        check_errors(errors)

        byte_split = split_bytes(msg.data[1])
        marks = check_marks(byte_split["l_byte"])
        print("Bike mark:", marks)

        state_n_gear(byte_split["h_byte"])
        rpm_value = assemble_bytes(low_byte=msg.data[2], high_byte=msg.data[3])
        print("RPM:", rpm_value)

        battery_voltage = assemble_bytes(low_byte=msg.data[4], high_byte=msg.data[5], divide=10)
        print("Battery voltage:", battery_voltage)
        battery_current = assemble_bytes(low_byte=msg.data[6], high_byte=msg.data[7], divide=10)
        print("Battery current:", battery_current)

        
        ################### 1023

    elif(msg.arbitration_id == can_ids["EM_CAN_ID2"]):
        print("\n*********** Second part of CAN message ***********")
        print("Controller temprature: ", msg.data[0])
        print("Motor temprature: ", msg.data[1])
        print("Motor pos", motor_position(msg.data[3]))
        print("Throttle signal: ", msg.data[4])
        print("Bike faults:", check_errors2(msg.data[6]))


os.system('sudo ifconfig can0 down')

