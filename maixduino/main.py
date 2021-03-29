from Maix import GPIO
from utime import sleep_us, ticks_us, sleep_ms
from machine import I2C
from fpioa_manager import fm
import sensor, image, lcd, usocket, ujson, machine, os, gc, sys
import KPU as kpu
from network_esp32 import wifi # code is in network_esp32.py (MUST BE IN ROOT OF SD CARD)

gc.collect()

# CONSTANTS
SLEEP_TIME = 500	# time in milliseconds to wait after distance measurement
ERROR_SLEEP_TIME = 4000	# time in milliseconds to show error in lcd before reset
DISTANCE_THRESHOLD_TEMP = 3	# DISTANCE in centimeters of how close the user has to be to ACTIVATE the TEMP SENSOR
DISTANCE_THRESHOLD_CAM = 27	# DISTANCE in centimeters of how close the user has to be to ACTIVATE the CAMERA
TEMP_MULTIPLIER = 1.13 # CALIBRATION MULTIPLIER for the TEMPERATURE readings
CLASSES = ["face mask", "face mask and face shield", "face shield", "no face", "none"]
IMG_SIZE = 128
SSID = "WIFI NAME"
PASSWORD  = "WIFI PASSWORD"
SERVER_ADDRESS = "SERVER IP"
PORT = 3000
HEADER_LENGTH = 7
FILE_NAME = "user_info.csv"

# INITIALIZE PINS
# 	pin registration
fm.register(22, fm.fpioa.GPIO3)
fm.register(23, fm.fpioa.GPIO4)
fm.register(24, fm.fpioa.GPIO5)
fm.register(32, fm.fpioa.GPIO6)
fm.register(15, fm.fpioa.GPIO7)
# 	pin assignment
trigger_cam = GPIO(GPIO.GPIO3, GPIO.OUT)
echo_cam = GPIO(GPIO.GPIO4, GPIO.IN)
buzzer = GPIO(GPIO.GPIO5, GPIO.OUT)
trigger_temp = GPIO(GPIO.GPIO6, GPIO.OUT)
echo_temp = GPIO(GPIO.GPIO7, GPIO.IN)
# 	initialize output pins to low
buzzer.value(0)
trigger_temp.value(0)
trigger_cam.value(0)

# INITIALIZE I2C (TEMP SENSOR)
i2c = I2C(I2C.I2C0, freq=115200, scl=30, sda=31)
i2c.scan()

# INITIALIZE CAMERA
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.run(1)

# INITIALIZE LCD
lcd.init()
lcd.rotation(2)
lcd.clear()

# INITIALIZE MODEL
task = kpu.load(0x200000) 
kpu.set_outputs(task, 0, 1, 1, 5)

# INITIALIZE FILE HANDLER
# 	create file and include column headers if file doesn't exist
if FILE_NAME not in os.listdir():
	with open(FILE_NAME, "w") as fout:
		column_headers = "name,contact_number,email,address,date_time,temperature,classification,confidence_level,cough_others,fever_others,headache_others,difficulty_breathing_others,cough,fever,headache,difficulty_breathing\n"
		fout.write(column_headers)

# RESET WHEN WIFI OR SOCKET CONNECTION IS LOST
def reset():
	lcd.clear()
	lcd.draw_string(20, 100, "ERROR: can't connect to wifi/server", lcd.RED, lcd.BLACK)
	lcd.draw_string(125, 120, "reseting...", lcd.RED, lcd.BLACK)
	sleep_ms(ERROR_SLEEP_TIME)
	machine.reset()

try:
	# INITIALIZE WIFI
	wifi.reset()
	wifi.connect(SSID, PASSWORD)

	# INITIALIZE SOCKET
	socket_client = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
	socket_client.connect((SERVER_ADDRESS, PORT)) # WON'T WORK IF SERVER IS NOT ON
	socket_client.settimeout(0)
except:
	reset()

# RETURNS THE DISTANCE, IN CENTIMETERS, FROM THE GIVEN ECHO AND TRIGGER PINS OF THE ULTRASONIC SENSOR
def get_distance(echo, trigger):
	# set trigger high for 10us
	trigger.value(1)
	sleep_us(10)
	trigger.value(0)
	
	# wait for echo to read high
	while echo.value() == 0: pass
	
	# get pulse width (duration where echo pin is high)
	t1 = ticks_us()
	while echo.value() == 1: pass
	t2 = ticks_us()
	pulse_width = t2 - t1
	
	# compute distance in centimeters
	distance = pulse_width / 58.0
	return distance
	
# TURN ON THE BUZZER FOR ms MILLISECONDS
def buzz(ms):
	buzzer.value(1)
	sleep_ms(ms)
	buzzer.value(0)
	
# RETURNS THE OBJECT TEMPERATURE READ BY THE TEMP SENSOR
def get_temp():
	# temp sensor's i2c address is 0x5A
	# temp sensor's object temp reading memory address is 0x07
	# read temp sensor's object temp readings
	readings = i2c.readfrom_mem(0x5A, 0x07, 2, mem_size=8)
	
	# first byte is low byte
	# second byte is high byte
	# combine the two bytes by shifting the high byte 8 bits and doing a bitwise or with the low byte
	temp = readings[0] | (readings[1] << 8)
	
	# compute temperature in degrees celcius
	temp = temp * 0.02 - 273.15
	return temp * TEMP_MULTIPLIER
	
# ENCAPSULATE data TOGETHER WITH THE type AND NECESSARY HEADER TO THE SOCKET SERVER
def send_data(data, type):
	try:
		data = bytes(data, "utf-8")
		data_length = len(data)
		header = bytes("{0: <{1}}".format(data_length, HEADER_LENGTH), "utf-8")
		payload = header + str(type) + data
		bytes_sent = 0
		while bytes_sent < HEADER_LENGTH + data_length + 1:
			sent = socket_client.send(payload[bytes_sent:])
			bytes_sent += sent
	except:
		reset()
		
# RECIEVE DATA FROM THE SOCKET SERVER
def recieve_data():
	try:
		bytes_recieved = 0
		header = b""
		while bytes_recieved < HEADER_LENGTH:
			chunk = socket_client.recv(min(HEADER_LENGTH - bytes_recieved, 1024))
			header += chunk
			bytes_recieved += len(chunk)
		data_length = int(header.decode("utf-8").strip(" "))
			
		type = b""
		while len(type) < 1:
			chunk = socket_client.recv(1)
			type += chunk
		type = int(type)
		
		bytes_recieved = 0
		data = b""
		while bytes_recieved < data_length:
			chunk = socket_client.recv(min(data_length - bytes_recieved, 1024))
			data += chunk
			bytes_recieved += len(chunk)

		return (type, data.decode("utf-8"))
	except:
		reset()

# main loop
print("starting...")

while True:
	try:
		# measure the user's DISTANCE from TEMP SENSOR
		distance_temp = get_distance(echo_temp, trigger_temp)
		if distance_temp <= DISTANCE_THRESHOLD_TEMP:
			# get the user's temperature and send it to the socket server
			temp = get_temp()
			send_data(str(temp), 1)
			buzz(100)
			sleep_ms(SLEEP_TIME // 2)		
		
		# measure the user's DISTANCE from the CAMERA
		distance_cam = get_distance(echo_cam, trigger_cam)
		if distance_cam <= DISTANCE_THRESHOLD_CAM:
			sleep_ms(100)
			# take a picture and display it on the lcd
			img = sensor.snapshot()
			lcd.display(img)
			# run the image through the model to get classification and send it to the server
			img = img.resize(IMG_SIZE, IMG_SIZE)
			img.pix_to_ai()
			res = kpu.forward(task, img)[:]
			res_max = max(res) 
			max_index = res.index(res_max)
			send_data(str(res_max * 100), 4)
			send_data(CLASSES[max_index], 2)
			buzz(100)
			sleep_ms(SLEEP_TIME)
			# image doesn't get garbage collected automatically when pix_to_ai() is called
			del img
		else:
			# take a picture and display it on the lcd
			img = sensor.snapshot()
			lcd.display(img)
			
		# ask for data
		send_data("", 0)
		type, data = recieve_data()
		if type != 0:
			# if data is not a ping message then save it to the csv file
			with open(FILE_NAME, "a") as fout:
				fout.write(data.replace('"', "") + "\n")
		
		# must wait at least 60ms before measuring distances again
		sleep_ms(60)
	except:
		socket_client.close()
		reset()



	
