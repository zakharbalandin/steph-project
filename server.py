import json
import threading
import sys
import serial
import time
import os
from hx711_weight import HX711
from http.server import BaseHTTPRequestHandler, HTTPServer

LOG_FILE = "sensor_log.txt"
MAX_LOG_SIZE = 100 * 1024 * 1024  # 100 МБ
log_lock = threading.Lock()
weights_lock = threading.Lock()
stop_event = threading.Event()

# Настройка датчиков
# hxs = [HX711(5, 6), HX711(17, 27), HX711(18, 19), HX711(22, 25)]
hxs = [HX711(5, 6), HX711(23, 24)]
current_weights = [0.0] * len(hxs)
PORT = 8080

class SensorHandler(BaseHTTPRequestHandler):
    """
    Обработчик HTTP-запросов для Wi-Fi передачи данных
    """
    def do_GET(self):
        if self.path == '/sensor':
            with weights_lock:
                response = {'values': current_weights[:len(hxs)]}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_data = json.dumps(response).encode('utf-8')
            self.wfile.write(response_data)
            log_data(f"Wi-Fi: Sent data: {response}")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
    
    def log_message(self, format, *args):
        return

def log_data(message):
    """Функция логирования с ротацией файла при превышении 100 МБ"""
    global log_lock
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    with log_lock:
        # Проверка размера лог-файла
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
            # Ротация логов
            backup_file = LOG_FILE.replace(".txt", ".old")
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.rename(LOG_FILE, backup_file)
            print(f"Log rotated. Old log saved as {backup_file}")
        
        # Запись в лог
        try:
            with open(LOG_FILE, 'a') as log_file:
                log_file.write(f"[{timestamp}] {message}\n")
        except IOError as e:
            print(f"Log error: {e}")

def hx_init_start():
    """
    Инициализация микросхем HX711 с повторными попытками
    """
    for hx in hxs:
        attempts = 5
        while attempts > 0:
            try:
                hx.reset()
                hx.set_gain_A(gain=64)
                hx.select_channel(channel='A')
                hx.get_data_mean(readings=10)
                hx.zero(readings=10)
                hx.get_data_mean(readings=10)
                print("HX711 initialized successfully")
                break
            except Exception as e:
                print(f"Initialization error: {e}")
                attempts -= 1
                if attempts == 0:
                    raise RuntimeError("Failed to initialize HX711 after multiple attempts")
                time.sleep(1)

def get_hx_data(hx):
    """
    Получение и обработка данных с датчика веса
    """
    try:
        val = hx.get_weight_mean(1)
        return abs(val) / 1000  # конвертация в кг
    except Exception as e:
        log_data(f"Sensor read error: {e}")
        return 0

def sensor_reader():
    """
    Поток чтения данных с датчиков
    """
    global current_weights
    print("Sensor reader started")
    
    while not stop_event.is_set():
        for i, hx in enumerate(hxs):
            weight = get_hx_data(hx)
            with weights_lock:
                current_weights[i] = weight
            log_data(f"Sensor {i} read: {weight:.3f} kg")
        time.sleep(0.5)  # Интервал чтения данных

def rs485_sender(ser):
    """
    Отправка данных по RS-485 в отдельном потоке
    """
    print("RS-485 sender started")
    last_sent = [0] * len(hxs)
    last_send_time = [0] * len(hxs)
    
    while not stop_event.is_set():
        current_time = time.time()
        
        for i in range(len(hxs)):
            # Отправка каждые 2 секунды для каждого датчика
            if current_time - last_send_time[i] >= 2:
                with weights_lock:
                    val = current_weights[i]
                
                kg_val = int(round(val, 1))
                
                if kg_val != last_sent[i]:
                    try:
                        ser.write(kg_val.to_bytes(2, byteorder='big'))
                        log_data(f"RS-485: Sensor {i} sent {kg_val} kg")
                        last_sent[i] = kg_val
                    except serial.SerialException as e:
                        log_data(f"RS-485 error: {e}")
                
                last_send_time[i] = current_time
        
        time.sleep(0.1)

def wifi_server(server):
    """
    Запуск Wi-Fi сервера в отдельном потоке
    """
    print(f"Wi-Fi server started on port {PORT}")
    print(f"Access at: http://<your_ip>:{PORT}/sensor")
    print("Wi-Fi network: RaspberryPi_Sensor")
    print("Password: None")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

def main():
    global stop_event
    
    print('RS-232/485 & Wi-Fi Gateway Started')
    
    # Инициализация последовательного порта
    try:
        ser = serial.Serial(
            port='/dev/serial0',
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
        )
        print("RS-485 port initialized")
    except serial.SerialException as e:
        log_data(f"Serial port error: {e}")
        sys.exit(1)
    
    # Инициализация сервера
    server = HTTPServer(('0.0.0.0', PORT), SensorHandler)
    
    # Инициализация датчиков
    try:
        hx_init_start()
    except Exception as e:
        log_data(f"Critical initialization error: {e}")
        ser.close()
        sys.exit(1)
    
    # Запуск потоков
    threads = [
        threading.Thread(target=sensor_reader, daemon=True),
        threading.Thread(target=rs485_sender, args=(ser,), daemon=True),
        threading.Thread(target=wifi_server, args=(server,), daemon=True)
    ]
    
    for thread in threads:
        thread.start()
    
    # Ожидание прерывания
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_event.set()
        
        # Очистка ресурсов
        for thread in threads:
            thread.join(timeout=2.0)
        
        server.shutdown()
        ser.close()
        print("All resources released. Goodbye!")

if __name__ == "__main__":
    main()