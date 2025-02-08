import serial
import time

def uart_transmitter_receiver(ser):
    """Функция для последовательной отправки и приема данных."""
    try:
        while True:
            # Отправка данных
            data_to_send = "hallo"
            print(f"Sending: {data_to_send.strip()}")
            ser.write(data_to_send.encode())
            ser.flush()

            # Ожидание ответа
            start_time = time.time()
            response = ""
            timeout = 2

            while (time.time() - start_time) < timeout:
                if ser.in_waiting > 0:
                    response += ser.read(ser.in_waiting).decode()
                    if '\n' in response:
                        response = response.split('\n')[0]
                        break
                time.sleep(0.1)

            # Вывод полученного ответа
            if response:
                print(f"Received: {response}")
            else:
                print("No response received within timeout.")

            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping by user request...")
    except serial.SerialException as e:
        print(f"Serial port error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        ser.close()
        print("Serial port closed.")

def main():
    # Настройка последовательного порта
    try:
        ser = serial.Serial(
            port='/dev/serial0',
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
        )
        print(f"Serial port {ser.port} opened successfully.")
    except serial.SerialException as e:
        print(f"Failed to open serial port: {e}")
        return

    # Очистка буферов перед началом работы
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # Запуск цикла отправки-приема
    uart_transmitter_receiver(ser)

if __name__ == "__main__":
    main()