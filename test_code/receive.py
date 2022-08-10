import os
import can
import binascii

os.system('sudo ip link set can0 type can bitrate 250000')
os.system('sudo ifconfig can0 up')

can0 = can.interface.Bus(channel = 'can0', bustype = 'socketcan')# socketcan_native

msg = can0.recv(10.0)
print ("Can data:", msg)


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


def check_marks(mark_list):
    mark_codes =    [
                    "lock moto", "brake", "cruise", "side brake"
                    ]
    for x in mark_list:
        print(mark_codes[x])


def state_n_gear(value):
    state = ['P', 'R', 'N', 'D']
    gears = ['1', '2', '3', 'S']

    s_value = value & 3
    g_value = (value >> 2) & 3
    print("Bike state: %s\nBike gear: %s" % 
        (state[s_value], gears[g_value]))
    return [s_value, g_value]


def split_bytes(byte_value):
    '''
    Splits a byte inte its higer and lower part
    0x2A -> [2, A]
    '''

    lower = byte_value & 15
    higher = (byte_value >> 4) & 15
    return {"h_byte":higher, "l_byte": lower}

def check_bits(byte_value):
    b=1
    trigger_list = []
    for x in range(8):
        if(byte_value&b): trigger_list.append(x)
        b=b<<1
    return trigger_list

def assemble_bytes(high_byte, low_byte, divide=0):
    if(divide):
        return ((high_byte<<8) + low_byte)/divide
    return (high_byte<<8) + low_byte

if msg is None:
    print('Timeout occurred, no message.')

else:
    print(f"time: {msg.timestamp}\narb id: {hex(msg.arbitration_id)}\ndlc: {msg.dlc}\ndata {binascii.hexlify(msg.data)}")

    print("in a for loop")
    #x = len(msg)
    msg_data=""
    try:
        for x in range(len(msg.data)):
            #print(binascii.hexlify(bytearray(msg.data[x])).decode('ascii'))
            #print("0", byte_data, sep='x', end=' ', flush=True)
            msg_data +="%0.2X" % msg.data[x] + ' '
    except IndexError as e:
        print("index error, out of bound:", e) 

    if msg_data: print("data:", msg_data)
    errors = check_bits(msg.data[0])
    check_errors(errors)

    byte_split = split_bytes(msg.data[1])
    marks = check_bits(byte_split["l_byte"])
    check_marks(marks)

    state_n_gear(byte_split["h_byte"])
    rpm_value = assemble_bytes(low_byte=msg.data[2], high_byte=msg.data[3])
    print("RPM:", rpm_value)

    battery_voltage = assemble_bytes(low_byte=msg.data[4], high_byte=msg.data[5], divide=10)
    print("Battery voltage:", battery_voltage)
    battery_current = assemble_bytes(low_byte=msg.data[6], high_byte=msg.data[7], divide=10)
    print("Battery current:", battery_current)

os.system('sudo ifconfig can0 down')

