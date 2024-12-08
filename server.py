import json
import threading
import sys
import serial
import time
from hx711_weight import HX711

hxs = [HX711(5, 6), HX711(17, 27), HX711(18, 19), HX711(22, 25)]
hx_val = [0, 0, 0, 0, 0, 0, 0, 0]

def hx_init_start():
    """
    Инициализация микросхем HX711.
    Количество попыток инициализации, необходимо указывать из-за возможных проблем с инициализацией датчика.
    """
    for hx in hxs:
        attempts = 5  # Количество попыток инициализации
        while attempts > 0:
            try:
                hx.reset()
                hx.set_gain_A(gain=64)
                hx.select_channel(channel='A')
                hx.get_data_mean(readings=10)
                hx.zero(readings=10)  # Здесь может возникнуть ошибка
                hx.get_data_mean(readings=10)
                break
            except Exception as e:
                print(f"Error during initialization: {e}")
                attempts -= 1
                if attempts == 0:
                    print("Failed to initialize HX711 after multiple attempts.")
                    raise
                time.sleep(1) 

def get_hx_data(hx):
    """
    Функция получения и первичной обработки данных с датчиков.
    """
    try:
        val = hx.get_weight_mean(1)
        return abs(val) / 1000
    except Exception:
        return 0


def rs485_sender(ser, hxs):
    """
    Отправка данных о весе через RS-485.
    Используем big-endian порядок битов для удобного декодирования на принимающей стороне.
    """
    try:
        while True:
            for i in range(len(hxs)):
                val = int(round(get_hx_data(hxs[i]), 1) * 10)
                print(f"Sensor {i}: {val/10} kg")
                ser.write(val.to_bytes(2, byteorder='big')) 
                time.sleep(1)
    except Exception as e:
        print(f"Error in rs485_sender: {e}")

def main():
    """
    Для инициализации последовательного порта используются стандартные настройки UART
    """
    ser = serial.Serial(
        port='/dev/ttyAMA0',
        baudrate=9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
    )
    hx_init_start()
    rs485_sender(ser, hxs)

if __name__ == "__main__":
    print("SERVER STARTED")
    main()