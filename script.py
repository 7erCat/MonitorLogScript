'''
import psutil, time

while True:
    with open("system_log.txt", "a") as f:
        f.write(f"{time.ctime()} | CPU: {psutil.cpu_percent()}% | GPU: {psutil.virtual_memory().percent}%\n")
    time.sleep(5)
'''

import ctypes
from ctypes import wintypes
import time
from datetime import datetime

# Настройка логгера
LOG_FILE = 'system_monitor.log'


# Структуры для Windows API
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)
    ]


class GPU_PERFORMANCE(ctypes.Structure):
    _fields_ = [
        ("Size", wintypes.DWORD),
        ("EnginesUtilization", ctypes.c_ulonglong * 8),
        ("FbUsage", ctypes.c_ulonglong),
        ("FbTotal", ctypes.c_ulonglong),
        ("GpuTemperature", ctypes.c_ulong)
    ]


def get_memory_info():
    """Получение информации о памяти"""
    mem_status = MEMORYSTATUSEX()
    mem_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem_status)):
        return {
            'load': mem_status.dwMemoryLoad,
            'total_gb': round(mem_status.ullTotalPhys / (1024 ** 3), 1),
            'free_gb': round(mem_status.ullAvailPhys / (1024 ** 3), 1)
        }
    return None


def get_cpu_usage():
    """Получение загрузки CPU"""

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD),
                    ("dwHighDateTime", wintypes.DWORD)]

    idle1 = FILETIME()
    kernel1 = FILETIME()
    user1 = FILETIME()
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle1),
                                          ctypes.byref(kernel1),
                                          ctypes.byref(user1))
    time.sleep(1)

    idle2 = FILETIME()
    kernel2 = FILETIME()
    user2 = FILETIME()
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle2),
                                          ctypes.byref(kernel2),
                                          ctypes.byref(user2))

    def to_uint64(filetime):
        return (filetime.dwHighDateTime << 32) + filetime.dwLowDateTime

    idle = to_uint64(idle2) - to_uint64(idle1)
    kernel = to_uint64(kernel2) - to_uint64(kernel1)
    user = to_uint64(user2) - to_uint64(user1)

    if kernel + user == 0:
        return 0
    return round((kernel + user - idle) / (kernel + user) * 100, 1)


def get_gpu_info():
    """Получение информации о GPU через NVIDIA API"""
    try:
        nvml = ctypes.windll.nvml
        if nvml.NvmlInit() != 0:
            return None

        device_count = ctypes.c_uint()
        nvml.NvmlDeviceGetCount(ctypes.byref(device_count))

        if device_count.value == 0:
            return None

        handle = ctypes.c_void_p()
        nvml.NvmlDeviceGetHandleByIndex(0, ctypes.byref(handle))

        # Получение температуры
        temp = ctypes.c_uint()
        nvml.NvmlDeviceGetTemperature(handle, 0, ctypes.byref(temp))

        # Получение использования памяти
        mem_info = GPU_PERFORMANCE()
        mem_info.Size = ctypes.sizeof(GPU_PERFORMANCE)
        nvml.NvmlDeviceGetPerformanceState(handle, ctypes.byref(mem_info))

        nvml.NvmlShutdown()

        return {
            'temp': temp.value,
            'load': round(mem_info.EnginesUtilization[0] / 100, 1),
            'mem_used': round(mem_info.FbUsage / (1024 ** 2), 1),
            'mem_total': round(mem_info.FbTotal / (1024 ** 2), 1)
        }
    except:
        return None


def log_metrics():
    """Запись метрик в лог-файл"""
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            # Получение метрик
            cpu = get_cpu_usage()
            mem = get_memory_info()
            gpu = get_gpu_info()

            # Формирование строки лога
            log_str = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "
            log_str += f"CPU: {cpu}% | "

            if mem:
                log_str += f"Memory: {mem['load']}% ({mem['free_gb']}/{mem['total_gb']} GB) | "
            else:
                log_str += "Memory: N/A | "

            if gpu:
                log_str += (f"GPU: {gpu['load']}% | Temp: {gpu['temp']}°C | "
                            f"VRAM: {gpu['mem_used']}/{gpu['mem_total']} MB")
            else:
                log_str += "GPU: N/A"

            # Запись в лог и вывод в консоль
            f.write(log_str + "\n")
            print(log_str)

    except Exception as e:
        print(f"Ошибка логирования: {str(e)}")


if __name__ == "__main__":
    print("Системный монитор запущен. Логи в system_monitor.log")
    print("Для выхода нажмите Ctrl+C\n")

    try:
        while True:
            log_metrics()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nМониторинг остановлен")