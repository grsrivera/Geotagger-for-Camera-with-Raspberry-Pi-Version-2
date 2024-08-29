import serial
import serial.tools.list_ports
import pickle
import os
import time
#import mouse # For Windows testing on laptop
import RPi.GPIO as GPIO

def open_ublox():
    VID_and_PID = 'VID:PID=1546:01A7'
    while True:
        ports = serial.tools.list_ports.comports(include_links=False)
        
        if not ports:
            print('Waiting for u-blox to connect...')
            time.sleep(5)
        else:
            for port in ports:
                # Check to see that USB is being read
                if VID_and_PID in port.hwid:
                    # Then open serial
                    try:
                        ublox = serial.Serial(port=port.device, baudrate=9600, timeout=0.1)
                        time.sleep(0.2)
                        return ublox
                    except serial.SerialException:
                        print('Close u-blox in other apps.')
                        time.sleep(5)
                        pass
            time.sleep(5)

def plot_fixes(ublox):
    ublox.reset_input_buffer()
    fix_dict = {} # Keys are dates, Values are list of fixes

    try: 
        while True:
            line = ublox.readline().decode()
            if '$GPRMC' in line:
#           	print('GPRMC in line')
                date = line.split(',')[9]
                date = f'20{date[4:6]}_{date[2:4]}_{date[0:2]}'
                if date not in fix_dict:
                    fix_dict[date] = []
            
            if '$GPGGA' in line:
                fix_dict[date].append(line)
#                 print('Good fix data')
                
            #if mouse.is_pressed("right"):
            #    time.sleep(0.2)
            #    break
            stop_button = GPIO.input(38)
            if stop_button == GPIO.LOW:
                time.sleep(0.2)
                break

    finally:
        print('Geotagging ended')
        # time.sleep(2.0)
        print(f'{ublox.in_waiting} bytes in buffer. Should be zero')
        
        if ublox.in_waiting > 0:
            print('Flushing buffer')
        while ublox.in_waiting > 0:
            line = ublox.readline().decode()
            if '$GPRMC' in line:
                date = line.split(',')[9]
                date = f'20{date[4:6]}_{date[2:4]}_{date[0:2]}'
                if date not in fix_dict:
                    fix_dict[date] = []
            
            if '$GPGGA' in line:
                fix_dict[date].append(line)
            if ublox.in_waiting == 0:
                print(f'Now {ublox.in_waiting} bytes in buffer.')
        
        return fix_dict

def save_file(fix_dict):
    # Maintain one pickle file per day, so append to existing file if there's already one
    folder_path = '/home/grivera/Desktop/gps_logs'
    # folder_path = 'C:/Users/geral/Documents/GitHub/Geotagger V2/list_files'
    
    fix_quantity = 0
    for date in fix_dict:
        if os.path.exists(f'{folder_path}/{date}.pkl'):
            with open(f'{folder_path}/{date}.pkl', 'rb') as file:
                existing_data = pickle.load(file)
                existing_data.extend(fix_dict[date])
                new_fixes = existing_data
        else:
            new_fixes = fix_dict[date]
        with open(f'{folder_path}/{date}.pkl', 'wb') as file:
            pickle.dump(new_fixes, file)
            file.flush()
            os.fsync(file.fileno())
    fix_quantity = fix_quantity + len(new_fixes)
    return len(fix_dict), fix_quantity

# For green button
def turn_on_again():
        while True:
        #if mouse.is_pressed("right"):
        #    time.sleep(0.5)
        #    break
        
            start_button = GPIO.input(10)
            stop_button = GPIO.input(38)
            time.sleep(0.2)
            if start_button == GPIO.LOW and stop_button == GPIO.HIGH:
                return 'collect_again'
            LED_control(7, 'flashing')
            
            if start_button == GPIO.LOW and stop_button == GPIO.LOW:
                return 'end'

def initialize_GPIO():
    GPIO.setmode(GPIO.BOARD)
    # output pins
    green_LED = 33
    yellow_LED = 7
    start_button = 10
    stop_button = 38
    
    GPIO.setup(green_LED, GPIO.OUT)
    GPIO.setup(yellow_LED, GPIO.OUT)
    GPIO.setup(start_button, GPIO.IN, GPIO.PUD_UP)
    GPIO.setup(stop_button, GPIO.IN, GPIO.PUD_UP)
    
    start_button = GPIO.input(start_button)
    stop_button = GPIO.input(stop_button)
    
    return green_LED, yellow_LED, start_button, stop_button
    
def LED_control(color, condition):
    if condition == 'flashing':
        GPIO.output(color, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(color, GPIO.LOW)
        time.sleep(0.5)
    elif condition == 'off':
        GPIO.output(color, GPIO.LOW)
    elif condition =='on':
        GPIO.output(color,GPIO.HIGH)

def main():
#     time.sleep(60) # Delay for USB when starting with crontab
    green_LED, yellow_LED, start_button, stop_button = initialize_GPIO()
    
    LED_control(yellow_LED, 'on')
    print('Connecting to u-blox')
    ublox = open_ublox()
    try:
        while True:
            LED_control(yellow_LED, 'off')
            LED_control(green_LED, 'on')
            print('\nu-blox connected and plotting fixes\n')
            fix_dict = plot_fixes(ublox) # With green flashing LED
            file_quantity, fix_quantity = save_file(fix_dict)
            print(f'{file_quantity} file(s) for a total of {fix_quantity} fix(es) saved') # Fix quant?
            print()
            LED_control(green_LED, 'off')
            status = turn_on_again() # With yellow flashing LED
            if status == 'collect_again':
                pass
            elif status == 'end':
                break
    finally:
        ublox.close()
        GPIO.cleanup()
        print('Made it to end')

if __name__ == '__main__':
    main()




