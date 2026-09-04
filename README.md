# Spine Alignment Detector

An Arduino and Python system for monitoring posture through changes in an accelerometer's orientation. This project was developed for the second homework assignment in **Praktikum iz merno-akvizicionih sistema**, academic year **2025/2026**.

The system calibrates a reference position, detects angular deviations from that reference, and counts them on both a desktop interface and a four-digit display. An LED provides an alert when a deviation continues for a user-defined duration.

## How it works

The Arduino reads the accelerometer every 100 ms using the TimerOne library and sends measurements to Python through a USB serial connection.

The application follows these stages:

1. **Start acquisition:** Pressing START in the interface enables sensor acquisition on the Arduino.
2. **Calibration:** Touching the capacitive sensor starts a three-second calibration. The user maintains the reference posture while Python averages the acceleration components and displays the reference values.
3. **Movement test:** A second touch starts an eight-second test. The user tilts forward and backward while the application records the maximum deviation angle.
4. **Threshold selection:** After the test, the user enters an angle threshold and a minimum duration for the LED alert, then presses POTVRDI to begin monitoring.
5. **Active monitoring:** Python calculates the angle between the current acceleration vector and the calibrated reference. It counts deviations, tracks their duration, and sends commands to the Arduino display and LED.
6. **Session export:** Pressing STOP ends acquisition and saves the session results to a text file.

A deviation is counted once when the angle first exceeds the threshold. The LED turns on when the continuous deviation reaches the selected minimum duration. Returning to or below the threshold turns the LED off and resets the continuous timer.

The counter includes both short and prolonged deviations. The minimum-duration setting controls the LED alert.

## System components

The project contains three connected parts:

- **Arduino firmware:** Sensor acquisition, touch detection through interrupts, serial communication, and control of the display and onboard LED.
- **Python processing:** Calibration, acceleration conversion, angle calculation, deviation counting, and session export.
- **PyQt5 interface:** Session controls, threshold inputs, measurements, and status messages.

Python reads serial messages in a background thread and passes them to the interface through a Qt signal. Both programs communicate at 9600 baud.

The Python application was developed in Spyder. The interface and source-code comments are in Serbian.

## Hardware

- Arduino UNO R3
- Analog three-axis accelerometer
- Capacitive touch sensor
- TM1637 four-digit seven-segment display
- Arduino onboard LED
- USB cable and connecting wires

The following connections are specified in the assignment for the supplied modules:

| Component | Component pin | Arduino pin |
| --- | --- | --- |
| TM1637 display | CLK | D9 |
| TM1637 display | DIO | D8 |
| TM1637 display | Vcc | 5V |
| TM1637 display | GND | GND |
| Capacitive touch sensor | I/O | D2 |
| Capacitive touch sensor | Vcc | 5V |
| Capacitive touch sensor | GND | GND |
| Accelerometer | X | A0 |
| Accelerometer | Y | A1 |
| Accelerometer | Z | A2 |
| Accelerometer | Vcc | 5V |
| Accelerometer | GND | GND |

The sketch controls the onboard LED through D13.

## Setup

### Arduino

Install these libraries in Arduino IDE:

- [TimerOne](https://github.com/PaulStoffregen/TimerOne)
- [TM1637Display](https://github.com/avishorp/TM1637)

Open the Arduino sketch, select Arduino UNO and the correct serial port, and upload it to the board.

Close the Arduino Serial Monitor before connecting from Python.

### Python

Install the dependencies in the Python environment used by Spyder:

```bash
python -m pip install PyQt5 pyserial
```

In the Python script, change the serial port to match the connected Arduino:

```python
self.serial_port_name = "COM5"
```

Run the Python script in Spyder and press START.

Keep the computer connected during monitoring because Python performs the calculations and sends commands to the display and LED.

To include the optional animation, place `bad_posture.gif` in the same folder as the Python script. The application also runs without it.

## Angle calculation

The reference acceleration vector is calculated by averaging the measurements collected during calibration.

The deviation angle is then calculated from the dot product of the current and reference vectors:

```text
angle = acos(dot(current, reference) / (norm(current) * norm(reference)))
```

The result is converted to degrees. The cosine value is limited to the range [-1, 1] before applying `acos` to prevent numerical rounding errors.

## Interface

The desktop interface displays:

- Current acceleration components: ax, ay, and az
- Calculated deviation angle
- Calibrated reference acceleration values
- Total number of detected deviations
- Total time spent above the angle threshold
- Current calibration, testing, or monitoring stage

The deviation count is also shown on the physical TM1637 display.

## Saved results

Pressing STOP saves the following information to `monitor_drzanja.txt`:

- Mean reference acceleration values: axcal, aycal, and azcal
- Total number of detected deviations
- Total time spent above the angle threshold

The file is saved in the current working directory. Each save overwrites its previous contents. Closing the application window stops monitoring without saving.

## Implementation notes

The assignment specifies an eight-second movement test but also mentions selecting the threshold after five seconds. This implementation completes the eight-second test before enabling threshold entry.

Touch events less than 300 ms apart are treated as one touch.

Conversion from raw sensor readings uses an offset of 337 and a sensitivity of 67 counts per g, with the X and Y axes inverted. These constants depend on the sensor and ADC setup. Reference-posture calibration averages the converted readings without recalculating these constants.

The measured angle represents sensor orientation relative to the calibrated reference. Movement-related acceleration and fluctuations around the threshold can affect detection. The current implementation does not apply filtering or hysteresis.
