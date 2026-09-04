Spine Alignment Detector

An Arduino and Python system for monitoring posture through changes in an accelerometer's orientation. The project was developed for the second homework assignment in Praktikum iz merno-akvizicionih sistema (13Е052ПМС), academic year 2025/2026.

The system establishes a reference position through calibration, detects angular deviations from that reference, and counts them on both a desktop interface and a four-digit display. An LED provides an alert when a deviation continues for a user-defined duration.

System design

The project consists of three parts:

Arduino firmware: reads the accelerometer and capacitive touch sensor, sends measurements to Python, and controls the display and onboard LED.

Python data processing: converts sensor readings into acceleration values, calculates the deviation angle, and tracks the number and duration of deviations.

PyQt5 interface: provides session controls, threshold settings, measurement displays, and status messages.

The Arduino and Python application communicate over USB serial at 9600 baud. A TimerOne interrupt requests acquisition every 100 ms, corresponding to a nominal sampling rate of 10 Hz. Touch detection uses an external interrupt on D2. Python reads serial messages in a background thread and passes them to the interface through a Qt signal.

How it works

Start acquisition. Pressing START in the Python interface enables sensor acquisition on the Arduino.

Calibrate the reference. A touch on the capacitive sensor starts a three-second calibration. The sensor remains still in the selected upright reference position while Python averages its acceleration components. The resulting reference values are displayed in the interface.

Test the movement range. A second touch starts an eight-second test. The user tilts the sensor forward and backward, and the application records the maximum deviation angle. After the test, the user enters an angle threshold and a minimum duration, then presses POTVRDI to begin monitoring.

Monitor deviations. The application compares the current acceleration vector with the reference vector using the dot product to calculate their angle. A new episode above the angle threshold adds one to the counter. The count appears in the interface and on the TM1637 display. If the episode reaches the selected minimum duration, the onboard LED turns on. Returning to or below the threshold turns it off and resets the continuous timer.

Stop and save. Pressing STOP ends acquisition and saves a summary of the session.

The counter includes short deviations as well as prolonged ones. The minimum-duration setting controls the LED alert. The total accumulated time includes all time spent above the angle threshold.

Hardware

Arduino UNO R3

Analog three-axis accelerometer

Capacitive touch sensor

TM1637 four-digit seven-segment display

Arduino onboard LED

USB cable and connecting wires

The following connections follow Table 1.1 of the assignment for the supplied modules:

Component

Component pin

Arduino pin

TM1637 display

CLK

D9

TM1637 display

DIO

D8

TM1637 display

Vcc

5V

TM1637 display

GND

GND

Capacitive touch sensor

I/O

D2

Capacitive touch sensor

Vcc

5V

Capacitive touch sensor

GND

GND

Accelerometer

X

A0

Accelerometer

Y

A1

Accelerometer

Z

A2

Accelerometer

Vcc

5V

Accelerometer

GND

GND

The sketch uses D13 to control the onboard LED. The assignment does not specify the accelerometer or touch-sensor model.

Software and setup

The Python application was developed in Spyder. Its interface and source comments are in Serbian.

Install the Python dependencies in the environment used to run the application:

python -m pip install PyQt5 pyserial

Install the Arduino libraries TimerOne and TM1637Display, then upload the Arduino sketch to the UNO R3.

In the Python script, set the serial port to match the board:

self.serial_port_name = "COM5"

Close the Arduino Serial Monitor, run the Python script in Spyder, and press START. Keep the computer connected during monitoring, since Python performs the calculations and sends display and LED commands to the Arduino.

The optional bad_posture.gif animation belongs in the same folder as the Python script. If it is absent, the application displays a message and continues running.

Interface and saved results

The interface displays the current acceleration components, calculated angle, calibrated reference values, deviation count, accumulated time above the threshold, and current session stage.

Pressing STOP writes the following to monitor_drzanja.txt in the current working directory:

Mean reference acceleration values: axcal, aycal, and azcal

Total number of detected deviations

Total time spent above the angle threshold

Each save overwrites the previous file. Closing the window stops the session without saving.

Implementation notes

The assignment specifies an eight-second movement test but also mentions choosing the threshold after five seconds. This implementation completes the full eight-second test before enabling threshold entry.

Touch events less than 300 ms apart are treated as one touch. The conversion from raw readings uses an offset of 337 and a sensitivity of 67 counts per g, with the X and Y axes inverted. These constants depend on the sensor and ADC setup; the reference-position calibration averages converted readings without changing the constants.

The measured angle represents sensor orientation relative to the calibrated reference. Movement-related acceleration and fluctuations around the threshold can affect detection. No filtering or hysteresis is applied in the current implementation.
