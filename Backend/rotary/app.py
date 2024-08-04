import RPi.GPIO as GPIO
import time
import os
import spidev
# import pymysql
import pymongo
from datetime import datetime

try:
    client = pymongo.MongoClient("mongodb://127.0.0.1:27017")
    db = client["Sensor_Data"]
    collection = db["test_28_march"]
except:
    print("*"*100)
    print("*"*100)
    print("*"*100)
    print("ROTARY SCRIPT CANNOT CONNECT TO MONGODB")
    print("*"*100)
    print("*"*100)
    print("*"*100)

actualt = 0
ltime = 0
eltime = 0
lastVal1 = 0
lastVal2 = 0
volume = 0
startTime = time.time()
debug = 0


class ADC_mcp3004:
    def __init__(self, bus=0, device=1):
        self.bus, self.device = bus, device
        self.spi = spidev.SpiDev()
        self.spi.open(0, 1)
        self.spi.max_speed_hz = 50000
        self.spi.mode = 1

    def open(self):
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = 50000

    def get_adc(self, channel):
        adc = self.spi.xfer2([1, (8 + channel) << 4, 0])
        adc_out = ((adc[1] & 3) << 8) + adc[2]
        voltage = (adc_out*3.3)/(1023)
        return adc_out

    def close(self):
        self.spi.close()


def mongoconnect(Barr_pulses, Gelcoat_pulses, Barrier_speedRPM, Gelcoat_speedRPM, WaterLevel_1, WaterLevel_2, Pressure):
    data = {
        "time": datetime.now().strftime('%Y-%m-%d %I:%M:%S %p'),
        "Barr_pulses": Barr_pulses,
        "Gelcoat_pulses": Gelcoat_pulses,
        "Barrier_speedRPM": Barrier_speedRPM,
        "Gelcoat_speedRPM": Gelcoat_speedRPM,
        "WaterLevel_1": WaterLevel_1,
        "WaterLevel_2": WaterLevel_2,
        "Pressure": Pressure
    }
    collection.insert_one(data)


def WaterLevel1m(adcVal):
    voltage1 = (adcVal/1023 * 5)
    meter1 = abs((voltage1-1)/4)
    # print(meter1)
    # meter_1=str.format(meter1)
    meter1 = round(meter1, 2)
    return meter1


def WaterLevel2m(adcVal):
    voltage2 = (adcVal/1023 * 5)
    meter2 = (voltage2-1)/2
# meter_2=str.format(meter2)
    meter2 = round(meter2, 2)
    return meter2


def PreSureVal(adcVal):
    voltage3 = (adcVal/1023 * 5)
    preSureraw = abs((voltage3-0.5)/4)
    pressure = 0.8*preSureraw
    # pressure1=str.format(pressure)
    pressure = round(pressure, 2)
    return pressure


sensor1 = ADC_mcp3004()
sensor2 = ADC_mcp3004()
sensor3 = ADC_mcp3004()


class Rotary:

    def __init__(self, Apin, Bpin, callback=None):
        self.Apin = Apin
        self.Bpin = Bpin
        self.value = 0
        self.state = '00'
        self.direction = None
        self.startt = 0
        self.eltime = 0
        self.dtime = 0
        self.rpm = 0
        self.callback = callback
        GPIO.setup(self.Apin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.Bpin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.Apin, GPIO.BOTH,
                              callback=self.transitionOccurred)
        GPIO.add_event_detect(self.Bpin, GPIO.BOTH,
                              callback=self.transitionOccurred)

    def transitionOccurred(self, channel):
        p1 = GPIO.input(self.Apin)
        p2 = GPIO.input(self.Bpin)
        newState = "{}{}".format(p1, p2)
        self.startt = time.process_time()

        if self.state == "00":  # Resting position
            if newState == "01":  # Turned right 1
                self.direction = "CW"
            elif newState == "10":  # Turned left 1
                self.direction = "L"

        elif self.state == "01":  # R1 or L3 position
            if newState == "11":  # Turned right 1
                self.direction = "CW"
            elif newState == "00":  # Turned left 1
                if self.direction == "CCW":
                    self.value = self.value - 1
                    self.dtime = time.process_time()-self.startt
                    self.rpm = (0.0157 * self.value)/self.dtime
                    if self.callback is not None:
                        self.callback(self.value, self.direction)

        elif self.state == "10":  # R3 or L1
            if newState == "11":  # Turned left 1
                self.direction = "CCW"
            elif newState == "00":  # Turned right 1
                if self.direction == "CW":
                    self.value = self.value + 1
                    self.dtime = time.process_time()-self.startt

                    self.rpm = (0.0157 * self.value)/self.dtime
                    if self.callback is not None:
                        self.callback(self.value, self.direction)

        else:  # self.state == "11"
            if newState == "01":  # Turned left 1
                self.direction = "CCW"
            elif newState == "10":  # Turned right 1
                self.direction = "CW"
            elif newState == "00":  # Skipped an intermediate 01 or 10 state, but if we know direction then a turn is complete
                if self.direction == "CCW":
                    self.value = self.value - 1
                    self.dtime = time.process_time()-self.startt
                    self.rpm = (0.0157 * self.value)/self.dtime
                    if self.callback is not None:
                        self.callback(self.value, self.direction)
                elif self.direction == "R":
                    self.value = self.value + 1
                    self.dtime = time.process_time()-self.startt
                    self.rpm = (0.0157 * self.value)/self.dtime
                    if self.callback is not None:
                        self.callback(self.value, self.direction)
        self.state = newState

    def getValue(self):
        return self.value

    def getrpm(self):
        return self.rpm


def valueChanged(value, direction):
    if (debug == 1):
        print("* countPos: {}, Direction: {} ".format(value, direction))


GPIO.setmode(GPIO.BCM)
#  GPIO.setup (17, GPIO.IN ,pull_up_down=GPIO.PUD_UP)
#  GPIO.setup (27, GPIO.IN ,pull_up_down=GPIO.PUD_UP)
e1 = Rotary(19, 26, valueChanged)  # barrier
e2 = Rotary(20, 21, valueChanged)  # gelcoat
prevTime = 0
# e2=Rotary(20,21,valueChanged)
try:
    while True:
        # ! Frequency of data saving
        time.sleep(1)
        newVal1 = e1.getValue()
        newVal2 = e2.getValue()
        time1 = time.time()-startTime
        # newVal2=e2.getValue()
        # if (newVal1>newVal2):
        #     print("rot 1")
        # else:
        #     print("rot2")
    #  pos=newVal1
        #  is Running
        value1 = sensor1.get_adc(channel=3)  # water level 2
        value2 = sensor2.get_adc(channel=0)  # water level 1
        value3 = sensor3.get_adc(channel=2)  # pressure sensor
        w1 = WaterLevel1m(value2)

        w2 = WaterLevel2m(value1)
        p1 = PreSureVal(value3)
        if (w1 < 0):
            w1 = abs(w1)
        if (w2 < 0):
            w2 = abs(w2)
        if (p1 < 0):
            p1 = abs(p1)
        dif1 = abs(newVal1-lastVal1)
        dif2 = abs(newVal2-lastVal2)
        rpmBarrier = (dif1 * 60)/400
        rpmGelcoat = (dif2 * 60)/400
        print("Barrier pulses:", dif1, "Gelcoat pulses:", dif2, "Barrier speed:",
              rpmBarrier, "Gelcoat speed:", rpmGelcoat, "w1:", w1, "w2:", w2, "p:", p1)
        water1 = abs(w1)
        water2 = abs(w2)
        p = abs(p1)
        mongoconnect(dif1, dif2, rpmBarrier, rpmGelcoat, water1, water2, p)
    #  mysqlconnect(dif1,dif2,rpmBarrier,rpmGelcoat,water1,water2,p)
        # print(time1-prevTime)
        # print ("rpm:",rpm)
        #  volume=volume+ newVal1/10
    #   print("volume is:",volume)
        #  IS not running

        # print("rpm:",rpm)
        lastVal1 = newVal1
        lastVal2 = newVal2
        # prevTime=time1
        # pos=0
except KeyboardInterrupt:
    pass
GPIO.cleanup()
