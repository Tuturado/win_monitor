import os
import sys
import time
import socket
import threading
import multiprocessing
import ctypes
import subprocess
from ctypes import wintypes
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import psutil
import qrcode

# Classe para leitura de CPU estilo Gerenciador de Tarefas do Windows
class WindowsTaskManagerCPU:
	def __init__(self):
		self.supported = False
		try:
			self.pdh = ctypes.windll.pdh
			self.query = wintypes.HANDLE()
			self.counter = wintypes.HANDLE()
			self.pdh.PdhOpenQueryW(None, 0, ctypes.byref(self.query))
			self.pdh.PdhAddEnglishCounterW(
				self.query,
				r"\Processor Information(_Total)\% Processor Utility",
				0,
				ctypes.byref(self.counter)
			)
			self.pdh.PdhCollectQueryData(self.query)
			self.supported = True
		except Exception:
			self.supported = False

	def get_cpu_percent(self):
		if not self.supported:
			return psutil.cpu_percent(interval=None)
		try:
			self.pdh.PdhCollectQueryData(self.query)

			class PDH_FMT_COUNTERVALUE(ctypes.Structure):
				class _VAL(ctypes.Union):
					_fields_ = [("longValue", ctypes.c_long), ("doubleValue", ctypes.c_double)]
				_fields_ = [("CStatus", wintypes.DWORD), ("val", _VAL)]

			fmt_val = PDH_FMT_COUNTERVALUE()
			self.pdh.PdhGetFormattedCounterValue(self.counter, 0x00000200, None, ctypes.byref(fmt_val))
			return round(fmt_val.val.doubleValue, 1)
		except Exception:
			return psutil.cpu_percent(interval=None)

win_cpu = WindowsTaskManagerCPU()

# Dicionário Global de Estatísticas
stats_data = {
	"cpu": 0.0,
	"ram": 0.0,
	"disk": 0.0,
	"net_download": "0 KB/s",
	"net_upload": "0 KB/s",
	"gpu": 0.0,
	"gpu_temp": 0.0,
	"gpu_status": "Off"
}

# GPU NVIDIA
gpu_available = False
try:
	import pynvml
	pynvml.nvmlInit()
	gpu_available = True
except Exception:
	gpu_available = False

def get_amd_or_generic_gpu():
	"""Lê utilização de GPUs AMD/Intel usando contadores do Windows"""
	usage = 0.0
	status = "Standby"
	try:
		cmd = 'powershell "Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine | Measure-Object -Property UtilizationPercentage -Sum | Select-Object -ExpandProperty Sum"'
		output = subprocess.check_output(cmd, shell=True, timeout=1, stderr=subprocess.DEVNULL).decode().strip()
		if output:
			usage = float(output)
			usage = min(100.0, round(usage, 1))
			status = "Ativa" if usage > 0 else "Pronta"
	except Exception:
		pass
	return usage, status

def resource_collector():
	last_net = psutil.net_io_counters()
	last_disk_io = psutil.disk_io_counters()
	last_time = time.time()

	while True:
		time.sleep(1.0)
		current_time = time.time()
		elapsed = current_time - last_time
		last_time = current_time

		# CPU, RAM
		cpu = win_cpu.get_cpu_percent()
		ram = psutil.virtual_memory().percent

		# Atividade de Disco
		curr_disk_io = psutil.disk_io_counters()
		disk_active_percent = 0.0

		if curr_disk_io and last_disk_io:
			try:
				busy_delta = curr_disk_io.busy_time - last_disk_io.busy_time
				disk_active_percent = (busy_delta / (elapsed * 1000.0)) * 100.0
			except AttributeError:
				read_delta = curr_disk_io.read_time - last_disk_io.read_time
				write_delta = curr_disk_io.write_time - last_disk_io.write_time
				total_time_delta = read_delta + write_delta
				disk_active_percent = (total_time_delta / (elapsed * 1000.0)) * 100.0

			disk_active_percent = min(100.0, max(0.0, disk_active_percent))

		last_disk_io = curr_disk_io

		# Velocidade de Rede
		curr_net = psutil.net_io_counters()
		bytes_recv = (curr_net.bytes_recv - last_net.bytes_recv) / elapsed
		bytes_sent = (curr_net.bytes_sent - last_net.bytes_sent) / elapsed
		last_net = curr_net

		def format_speed(b_s):
			if b_s >= 1024 * 1024:
				return f"{b_s / (1024 * 1024):.1f} MB/s"
			return f"{b_s / 1024:.0f} KB/s"

		# GPU
		gpu_usage = 0.0
		gpu_temp = 0.0
		gpu_status = "Standby"

		if gpu_available:
			try:
				device_count = pynvml.nvmlDeviceGetCount()
				for i in range(device_count):
					handle = pynvml.nvmlDeviceGetHandleByIndex(i)

					# Leitura individual de uso
					try:
						usage = float(pynvml.nvmlDeviceGetUtilizationRates(handle).gpu)
					except Exception:
						usage = 0.0

					# Leitura individual de temperatura (0 = NVML_TEMPERATURE_GPU)
					try:
						temp = float(pynvml.nvmlDeviceGetTemperature(handle, 0))
					except Exception:
						temp = 0.0

					if temp > 0 or usage > 0:
						gpu_usage = usage
						gpu_temp = temp
						gpu_status = "Ativa" if usage > 0 else "Pronta"
						break
			except Exception:
				gpu_status = "Standby"

		# Fallback para AMD/Genérica se NVIDIA falhar ou estiver em Standby
		if gpu_status == "Standby" or not gpu_available:
			amd_usage, amd_status = get_amd_or_generic_gpu()
			if amd_usage > 0:
				gpu_usage = amd_usage
				gpu_status = amd_status

		stats_data["cpu"] = cpu
		stats_data["ram"] = round(ram, 1)
		stats_data["disk"] = round(disk_active_percent, 1)
		stats_data["net_download"] = format_speed(bytes_recv)
		stats_data["net_upload"] = format_speed(bytes_sent)
		stats_data["gpu"] = round(gpu_usage, 1)
		stats_data["gpu_temp"] = round(gpu_temp, 1)
		stats_data["gpu_status"] = gpu_status

collector_thread = threading.Thread(target=resource_collector, daemon=True)
collector_thread.start()

app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

@app.get("/api/stats")
def get_stats():
	return stats_data

def get_local_ip():
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(("8.8.8.8", 80))
		local_ip = s.getsockname()[0]
		s.close()
		return local_ip
	except Exception:
		return "127.0.0.1"

def get_resource_path(relative_path: str) -> str:
	if hasattr(sys, '_MEIPASS'):
		return os.path.join(sys._MEIPASS, relative_path)
	return os.path.join(os.path.abspath("."), relative_path)

static_path = get_resource_path("static")
if os.path.exists(static_path):
	app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

if __name__ == "__main__":
	multiprocessing.freeze_support()

	port = 3001
	ip_local = get_local_ip()
	url = f"http://{ip_local}:{port}"

	print("\n" + "="*50)
	print(" 🚀 PC MONITOR INICIADO COM SUCESSO!")
	print("="*50)
	print(f" 📱 Abra o navegador no seu celular e digite:")
	print(f" 👉 {url}\n")
	print(" 🔍 Ou aponte a câmera do celular para o QR Code abaixo:")
	print("-" * 50)

	qr = qrcode.QRCode(border=2)
	qr.add_data(url)
	qr.make(fit=True)
	qr.print_ascii(invert=True)

	print("="*50 + "\n")

	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=port)