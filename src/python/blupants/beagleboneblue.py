import sys
import os
import time
import random
import json
import rcpy
import rcpy.motor as motor
import rcpy.servo as servo
import rcpy.clock as clock
import rcpy.gpio as gpio
from rcpy.gpio import InputEvent
import Adafruit_BBIO.GPIO as GPIO

try:
    import robots_common
except:
    import blupants.robots_common as robots_common


global default_config
default_config = robots_common.default_config


class BeagleBoneBlue(robots_common.RobotHollow):
    def __init__(self, config={}, config_file=""):
        super().__init__()
        self.running = False
        self.config = config
        self.config_file = config_file
        self.name = "BeagleBoneBlue"
        self._load_config()
        period = 0.02
        if "period" in self.config:
            period = self.config["period"]

        self.bbb_servos = [servo.Servo(1), servo.Servo(2), servo.Servo(3), servo.Servo(4), servo.Servo(5),
                           servo.Servo(6), servo.Servo(7), servo.Servo(8)]

        self.clcks = [clock.Clock(self.bbb_servos[0], period), clock.Clock(self.bbb_servos[1], period),
                      clock.Clock(self.bbb_servos[2], period), clock.Clock(self.bbb_servos[3], period),
                      clock.Clock(self.bbb_servos[4], period), clock.Clock(self.bbb_servos[5], period),
                      clock.Clock(self.bbb_servos[6], period), clock.Clock(self.bbb_servos[7], period)]

        self.motors = [motor.Motor(1), motor.Motor(2), motor.Motor(3), motor.Motor(4)]

        # Boot
        GPIO.cleanup()
        rcpy.set_state(rcpy.RUNNING)
        # disable servos
        servo.enable()
        # start clock
        for i in range(0, 8):
            self.clcks[i].start()
        self.running = True

    def _load_config(self):
        if len(self.config_file) and os.path.isfile(self.config_file):
            with open(self.config_file, "r") as f:
                json.load(self.config, f)
        for key in default_config:
            if key not in self.config:
                self.config[key] = default_config[key]
        if "name" in self.config:
            self.name = self.config.get("name")

    def shutdown(self, quiet=False):
        self.print_stdout("shutdown(quiet={})".format(quiet), quiet)
        self.running = False
        # stop clock
        for i in range(0, 8):
            self.clcks[i].stop()
        # disable servos
        servo.disable()
        rcpy.set_state(rcpy.EXITING)
        GPIO.cleanup()

    def sleep(self, seconds=1.0, quiet=False):
        self.print_stdout("sleep(seconds={})".format(seconds), quiet)
        time.sleep(seconds)

    def set_servo(self, i=1, angle=0.0, quiet=False):
        self.print_stdout("set_servo(i={}, angle={})".format(i, angle), quiet)
        time.sleep(0.2)
        if angle > 0 and angle > 90:
            angle = 90
        if angle < 0 and angle < -90:
            angle = -90
        position = angle * 0.015
        self.bbb_servos[i - 1].set(position)
        time.sleep(0.2)

    def set_motor(self, i=1, duty=0.5, quiet=False):
        self.print_stdout("set_motor(i={}, duty={})".format(i, duty), quiet)
        motor_index = i-1
        self.motors[motor_index].set(duty)


class BluPants(BeagleBoneBlue):
    def __init__(self, config={}, config_file=""):
        self.duty = 0.5
        self.duty_ratio = [1.0, 1.0, 1.0, 1.0]
        self.turn_right_period = 0.005
        self.turn_left_period = 0.005
        self.motor_front_left = 1
        self.motor_front_right = 2
        self.motor_back_left = 3
        self.motor_back_right = 4
        self.grab = True
        self.echo = "P9_23"
        self.trigger = "GPIO1_25"
        self.servo_claw = 8
        self.servo_claw_angle_open = -45.0
        self.servo_claw_angle_close = 45.0
        super().__init__(config, config_file)

        # Boot
        # Configuration
        GPIO.setup(self.trigger , GPIO.OUT)  # Trigger
        GPIO.setup(self.echo, GPIO.IN)  # Echo
        GPIO.output(self.trigger, False)

    def _load_config(self):
        super()._load_config()
        if "blupants" in self.config:
            if "motor" in self.config["blupants"]:
                if "duty_ratio" in self.config["blupants"]["motor"]:
                    self.duty_ratio = self.config["blupants"]["motor"]["duty_ratio"]
                if "turn_right_period" in self.config["blupants"]["motor"]:
                    self.turn_right_period = self.config["blupants"]["motor"]["turn_right_period"]
                if "turn_left_period" in self.config["blupants"]["motor"]:
                    self.turn_left_period = self.config["blupants"]["motor"]["turn_left_period"]
                if "position" in self.config["blupants"]["motor"]:
                    if "front_left" in self.config["blupants"]["motor"]["position"]:
                        self.motor_front_left = self.config["blupants"]["motor"]["position"]["front_left"]
                    if "front_right" in self.config["blupants"]["motor"]["position"]:
                        self.motor_front_right = self.config["blupants"]["motor"]["position"]["front_right"]
                    if "back_left" in self.config["blupants"]["motor"]["position"]:
                        self.motor_back_left = self.config["blupants"]["motor"]["position"]["back_left"]
                    if "back_right" in self.config["blupants"]["motor"]["position"]:
                        self.motor_back_right = self.config["blupants"]["motor"]["position"]["back_right"]
            if "claw" in self.config["blupants"]:
                if "servo" in self.config["blupants"]["claw"]:
                    self.servo_claw = self.config["blupants"]["claw"]["servo"]
                if "angle_open" in self.config["blupants"]["claw"]:
                    self.servo_claw_angle_open = self.config["blupants"]["claw"]["angle_open"]
                if "angle_close" in self.config["blupants"]["claw"]:
                    self.servo_claw_angle_close = self.config["blupants"]["claw"]["angle_close"]

    def _distance_measurement(self):
        max = 10000
        GPIO.output(self.trigger, True)
        time.sleep(0.00001)
        GPIO.output(self.trigger, False)
        pulse_start = time.time()
        pulse_end = time.time()
        counter = 0
        while GPIO.input(self.echo) == 0:
            pulse_start = time.time()
            counter += 1
            if counter > max:
                return -1
        counter = 0
        while GPIO.input(self.echo) == 1:
            pulse_end = time.time()
            counter += 1
            if counter > max:
                return -1

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150
        distance = round(distance, 2)
        return distance

    def claw_toggle(self, quiet=False):
        if self.grab:
            self.claw_close(quiet)
        else:
            self.claw_open(quiet)

    def claw(self, quiet=False):
        return self.claw_toggle(quiet)

    def claw_open(self, quiet=False):
        self.print_stdout("claw_open()", quiet)
        self.grab = True
        self.set_servo(self.servo_claw, self.servo_claw_angle_open, quiet=True)

    def claw_close(self, quiet=False):
        self.print_stdout("claw_close()", quiet)
        self.grab = False
        self.set_servo(self.servo_claw, self.servo_claw_angle_close, quiet=True)

    def read_distance(self, quiet=False):
        distance = 0
        # Read sonar
        distance = self._distance_measurement()
        try:
            system = self.config.get("measurement_system").lower()
        except:
            system = "m"
        if system == "r" or system == "i" or system == "b":
            distance = distance * 0.393701
            self.print_stdout("Distance: [{}] inches.".format(str(distance)), quiet)
        else:
            self.print_stdout("Distance: [{}] cm.".format(str(distance)), quiet)
        return distance

    def move(self, period=1, duty=1, quiet=False):
        self.print_stdout("move(period={}, duty={})".format(period, duty), quiet)
        self.duty = duty
        for i in range(1, 5):
            self.set_motor(i, duty * self.duty_ratio[i-1], quiet=True)
        self.sleep(period, quiet=True)
        for i in range(1, 5):
            self.set_motor(i, 0, quiet=True)

    def move_forward(self, blocks=1, speed=0.5, quiet=False):
        self.print_stdout("move_forward(blocks={}, speed={})".format(blocks, speed), quiet)
        period = blocks/speed
        self.move(period, speed, quiet=True)

    def move_backwards(self, blocks=1, speed=0.5, quiet=False):
        self.print_stdout("move_backwards(blocks={}, speed={})".format(blocks, speed), quiet)
        period = blocks/speed
        self.move(period, speed*-1, quiet=True)

    def turn_right(self, angle=90, quiet=False):
        self.print_stdout("turn_right(angle={})".format(angle), quiet)

        duty = 0.3  # Use fixed duty cycle for turning

        # Left
        self.set_motor(self.motor_front_left, duty, quiet=True)
        self.set_motor(self.motor_back_left, duty, quiet=True)
        # Right
        self.set_motor(self.motor_front_right, duty*-1, quiet=True)
        self.set_motor(self.motor_back_right, duty*-1, quiet=True)

        self.sleep(angle * self.turn_right_period, quiet=True)

        self.set_motor(self.motor_front_left, 0, quiet=True)
        self.set_motor(self.motor_back_left, 0, quiet=True)
        self.set_motor(self.motor_front_right, 0, quiet=True)
        self.set_motor(self.motor_back_right, 0, quiet=True)

    def turn_left(self, angle=90, quiet=False):
        self.print_stdout("turn_left(angle={})".format(angle), quiet)

        duty = 0.3  # Use fixed duty cycle for turning

        # Left
        self.set_motor(self.motor_front_left, duty*-1, quiet=True)
        self.set_motor(self.motor_back_left, duty*-1, quiet=True)
        # Right
        self.set_motor(self.motor_front_right, duty, quiet=True)
        self.set_motor(self.motor_back_right, duty, quiet=True)

        self.sleep(angle * self.turn_right_period, quiet=True)

        self.set_motor(self.motor_front_left, 0, quiet=True)
        self.set_motor(self.motor_back_left, 0, quiet=True)
        self.set_motor(self.motor_front_right, 0, quiet=True)
        self.set_motor(self.motor_back_right, 0, quiet=True)


class BluPantsCar(BluPants):
    def __init__(self, config={}, config_file=""):
        super().__init__(config, config_file)
        self.servo_horizontal = 1
        self.servo_vertical = 2
        self.camera_pos = 0
        self.camera_toggle_positions = [
            [-89.0, 0], [89.0, 0], [89.0, 30.0], [0, 30.0], [-89.0, 30.0], [-89.0, 0], [-89.0, -30.0], [0, -30.0],
            [89.0, -30.0], [89.0, 0], [0, 0]
        ]

        if "blupants" in self.config:
            if "camera" in self.config["blupants"]:
                if "servo_horizontal" in self.config["blupants"]["camera"]:
                    self.servo_horizontal = self.config["blupants"]["camera"]["servo_horizontal"]
                if "servo_vertical" in self.config["blupants"]["camera"]:
                    self.servo_vertical = self.config["blupants"]["camera"]["servo_vertical"]

    def camera_toggle(self, quiet=False):
        self.print_stdout("camera_toggle()", quiet)
        max = len(self.camera_toggle_positions)
        if self.camera_pos >= max:
            self.camera_pos = 0
        pos = self.camera_toggle_positions[self.camera_pos]
        self.sleep(0.2, quiet=True)
        self.set_servo(self.servo_horizontal, pos[0], quiet=True)
        self.sleep(0.2, quiet=True)
        self.set_servo(self.servo_vertical, pos[1], quiet=True)
        self.sleep(0.2, quiet=True)
        self.camera_pos += 1

    def look_angle(self, angle=90, quiet=False):
        self.print_stdout("look_angle(angle={})".format(angle), quiet)
        self.sleep(0.2, quiet=True)
        if angle > 0 and angle > 90:
            angle = 90
        if angle < 0 and angle < -90:
            angle = -90
        position = angle * 0.015
        self.set_servo(self.servo_horizontal, position, quiet=True)
        self.set_servo(self.servo_vertical, 0, quiet=True)
        self.sleep(0.2, quiet=True)

    def say_yes(self, quiet=False):
        self.print_stdout("say_yes()", quiet)
        self.look_angle(0, quiet=True)
        self.set_servo(self.servo_vertical, 60.0, quiet=True)
        self.set_servo(self.servo_vertical, -60.0, quiet=True)
        self.set_servo(self.servo_vertical, 60.0, quiet=True)
        self.look_angle(0, quiet=True)

    def say_no(self, quiet=False):
        self.print_stdout("say_no()", quiet)
        self.look_angle(0, quiet=True)
        self.set_servo(self.servo_horizontal, 60.0, quiet=True)
        self.set_servo(self.servo_horizontal, -60.0, quiet=True)
        self.set_servo(self.servo_horizontal, 60.0, quiet=True)
        self.look_angle(0, quiet=True)


class EduMIP(BluPants):
    def __init__(self, config={}, config_file=""):
        super().__init__(config, config_file)
        self.block_length = 0.28
        self.turn_coefficient = 0.0175
        self.meter_coefficient = 14
        self.servo_shoulder_left = 7
        self.servo_shoulder_right = 6
        self.servo_claw_angle_open = 45.0
        self.servo_claw_angle_close = 30.0
        self.var_dir = os.path.join(os.sep, "tmp", os.sep, "blupants")
        print("Make sure you have eduMPI balanced before running this script.")
        print("#rc_balance_dstr -i dstr")
        if "EduMIP" in self.config:
            if "block_length" in self.config["EduMIP"]:
                self.block_length = self.config["EduMIP"]["block_length"]
            if "turn_coefficient" in self.config["EduMIP"]:
                self.turn_coefficient = self.config["EduMIP"]["turn_coefficient"]
            if "meter_coefficient" in self.config["EduMIP"]:
                self.meter_coefficient = self.config["EduMIP"]["meter_coefficient"]
            if "servo_shoulder_left" in self.config["EduMIP"]:
                self.servo_shoulder_left = self.config["EduMIP"]["servo_shoulder_left"]
            if "servo_shoulder_right" in self.config["EduMIP"]:
                self.servo_shoulder_right = self.config["EduMIP"]["servo_shoulder_right"]
            if "claw" in self.config["EduMIP"]:
                if "angle_open" in self.config["EduMIP"]["claw"]:
                    self.servo_claw_angle_open = self.config["EduMIP"]["claw"]["angle_open"]
                if "angle_close" in self.config["EduMIP"]["claw"]:
                    self.servo_claw_angle_close = self.config["EduMIP"]["claw"]["angle_close"]

    def _create_cmd_file(self, cmd):
        file_path = os.path.join(self.var_dir, cmd)
        open(file_path, 'a').close()

    def move(self, distance_meter=1.0, quiet=False):
        self.print_stdout("move(distance_meter={})".format(distance_meter), quiet)
        if distance_meter > 0:
            self._create_cmd_file("up.txt.")
        else:
            self._create_cmd_file("down.txt.")
        self.sleep(self.meter_coefficient * distance_meter, quiet=True)
        self._create_cmd_file("break.txt.")
        self.sleep(2, quiet=True)

    def move_forward(self, blocks=1, quiet=False):
        self.print_stdout("move_forward(blocks={})".format(blocks), quiet)
        self.move(self.block_length*blocks, quiet=True)

    def move_backwards(self, blocks=1, quiet=False):
        self.print_stdout("move_backwards(blocks={})".format(blocks), quiet)
        self.move(self.block_length*blocks*-1, quiet=True)

    def turn_left(self, angle=90.0, quiet=False):
        self.print_stdout("turn_left(angle={})".format(angle), quiet)
        self._create_cmd_file("left.txt.")
        self.sleep(self.turn_coefficient * angle, quiet=True)
        self._create_cmd_file("break.txt.")
        self.sleep(2, quiet=True)

    def turn_right(self, angle=90.0, quiet=False):
        self.print_stdout("turn_right(angle={})".format(angle), quiet)
        self._create_cmd_file("right.txt.")
        self.sleep(self.turn_coefficient * angle, quiet=True)
        self._create_cmd_file("break.txt.")
        self.sleep(2, quiet=True)

    def claw_open(self, quiet=False):
        self.print_stdout("claw_open()", quiet)
        self.grab = True
        self.set_servo(self.servo_shoulder_left, self.servo_claw_angle_open * -1, quiet=True)
        self.set_servo(self.servo_shoulder_right, self.servo_claw_angle_open, quiet=True)

    def claw_close(self, quiet=False):
        self.print_stdout("claw_close()", quiet)
        self.grab = False
        self.set_servo(self.servo_shoulder_left, self.servo_claw_angle_close, quiet=True)
        self.set_servo(self.servo_shoulder_right, self.servo_claw_angle_close * -1, quiet=True)

    def say_no(self, quiet=False):
        self.print_stdout("say_no()", quiet)
        self.set_servo(self.servo_shoulder_left, 0, quiet=True)
        self.set_servo(self.servo_shoulder_right, 0, quiet=True)
        self.sleep(0.2, quiet=True)
        self.set_servo(self.servo_shoulder_right, -45, quiet=True)
        self.set_servo(self.servo_shoulder_left, -45, quiet=True)
        self.sleep(0.2, quiet=True)
        self.set_servo(self.servo_shoulder_left, 45, quiet=True)
        self.set_servo(self.servo_shoulder_right, 45, quiet=True)
        self.sleep(0.2, quiet=True)
        self.set_servo(self.servo_shoulder_right, 0, quiet=True)
        self.set_servo(self.servo_shoulder_left, 0, quiet=True)

    def say_yes(self, quiet=False):
        self.print_stdout("say_yes()", quiet)
        self.set_servo(self.servo_shoulder_left, 0, quiet=True)
        self.set_servo(self.servo_shoulder_right, 0, quiet=True)
        self.sleep(0.2, quiet=True)
        self.set_servo(self.servo_shoulder_right, 80, quiet=True)
        self.set_servo(self.servo_shoulder_left, -80, quiet=True)
        self.sleep(0.2, quiet=True)
        self.set_servo(self.servo_shoulder_left, 80, quiet=True)
        self.set_servo(self.servo_shoulder_right, -80, quiet=True)
        self.sleep(0., quiet=True)
        self.set_servo(self.servo_shoulder_right, 0, quiet=True)
        self.set_servo(self.servo_shoulder_left, 0, quiet=True)

