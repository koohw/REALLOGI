import time

device0 = "/sys/bus/iio/devices/iio:device0"

def readFirstLine(filename):
    retries = 5
    while retries > 0:
        try:
            with open(filename, "rt") as f:
                value = int(f.readline())
                return True, value
        except ValueError as e:
            print(f"ValueError: {e} while reading {filename}")
            return False, -1
        except OSError as e:
            print(f"OSError: {e} while reading {filename}. Retrying...")
            retries -= 1
            time.sleep(1)  # Wait a bit before retrying
    return False, 0

try:
    while True:
        Flag, Temperature = readFirstLine(device0 + "/in_temp_input")
        print("Temperature:", end="")
        if Flag:
            print(Temperature / 1000.0, "\u2103", end="\t")
        else:
            print("N.A.", end="\t")
        
        Flag, Humidity = readFirstLine(device0 + "/in_humidityrelative_input")
        print("Humidity:", end="")
        if Flag:
            print(Humidity / 1000.0, "%")
        else:
            print("N.A.")
        
        time.sleep(2.0)
except KeyboardInterrupt:
    pass
