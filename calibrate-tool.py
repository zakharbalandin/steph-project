import sys
import re
from hx711_weight import HX711

def hx_init_start(hx):
    """
    Инициализация HX711.
    """
    hx.reset()
    hx.set_gain_A(gain=64)
    hx.select_channel(channel='A')
    hx.zero(readings=10)

def calibrate_hx(known_weight: float, hx: HX711):
    """
    Калибровка HX711.
    """
    known_weight = known_weight * 1000  # Преобразование в граммы
    data = hx.get_data_mean(readings=30)
    ratio = data / known_weight
    return ratio

def calibrate():
    """
    Основная логика калибровки.
    """
    print("Введите пины подключения датчика в формате xx,yy:")
    hx = None  # Объект HX711 будет инициализирован позже

    for line in sys.stdin:
        line = line.strip()
        
        # Проверяем, соответствует ли ввод формату xx,yy
        match = re.match(r'(\d+),(\d+)', line)
        if match and hx is None:
            pin_in, pin_out = int(match.group(1)), int(match.group(2))
            print(f"Пины для калибровки установлены: {pin_in} и {pin_out}")
            hx = HX711(pin_in, pin_out)
            hx_init_start(hx)
            print("Инициализация завершена. Поместите известный груз на датчик и введите его вес в килограммах:")
        
        # Если датчик уже инициализирован, ожидаем ввод веса
        elif hx is not None and line.isdigit():
            known_weight = float(line)
            print(f"Начата калибровка с весом {known_weight} кг")
            ratio = calibrate_hx(known_weight, hx)
            print(f"Калибровочный коэффициент: {ratio}")
            print("Введите новые пины для продолжения калибровки или 'Exit' для выхода:")
        
        # Проверяем команду выхода
        elif line.lower() == "exit":
            break
        
        # Неверный ввод
        else:
            print("Неверный формат ввода. Повторите попытку.")

    print("Калибровка завершена.")

def main():
    print("ИНСТРУМЕНТ КАЛИБРОВКИ ЗАПУЩЕН")
    calibrate()

if __name__ == "__main__":
    main()
