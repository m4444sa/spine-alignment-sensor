import sys
import os
import time
import math
import threading

import serial

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QMovie, QFont

# Glavna klasa, osnovni prozor aplikacije
class PostureMonitor(QWidget):
    #PyQt Signal -> veza sa arduinom, arduino salje string
    data_received = pyqtSignal(str)

    #konstruktor
    def __init__(self):
        
        #konstruktor nadklase qwidget
        super().__init__()
    
        # Definisanje pocetnih vrednosti, konstanti i boolova
        self.serial_port_name = "COM5" 
        
        self.serial_port = None
        self.is_reading = False

        self.state = "IDLE"

    #Trajanje kalibracije i testiranja
        self.calibration_duration = 3.0
        self.test_duration = 8.0

        self.ax = 0.0
        self.ay = 0.0
        self.az = 0.0
        self.angle = 0.0

        self.ax_cal = 0.0
        self.ay_cal = 0.0
        self.az_cal = 9.81 

        self.calibration_samples = []
        self.calibration_start_time = None

        self.test_start_time = None
        self.max_test_angle = 0.0

        self.violation_count = 0
        self.total_bad_time = 0.0
        self.continuous_bad_time = 0.0
        self.was_bad = False

        self.last_sample_time = None
        self.led_state = 0
        self.threshold_deg= None
        self.min_bad_time_sec=None
        
        # Kada se emituje signal 'data_received', PyQt automatski 
        # poziva funkciju 'process_data_line' u glavnoj niti.
        self.data_received.connect(self.process_data_line)

        self.init_ui()

    # GRAFICKI INTERFEJS * do linije 363
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def init_ui(self):
        self.setWindowTitle("Monitor držanja kičme")

        #Aplikacija zauzima ceo prozor
        screen = QApplication.primaryScreen().availableGeometry()
        window_width = int(screen.width())
        window_height = int(screen.height())

        self.resize(window_width, window_height)
        #centriranje
        self.move(
            screen.x() + (screen.width() - window_width) // 2,
            screen.y() + (screen.height() - window_height) // 2
        )

        self.setFont(QFont("Helvetica", 12))

        #css stylesheet
        self.setStyleSheet("""
            QWidget {
                background-color: #F2FBF2;
                color: #1F3D2B;
                font-family: Helvetica, Arial;
            }
            QLabel {
                font-size: 17px;
            }
            QLineEdit {
                background-color: white;
                border: 2px solid #B7E4C7;
                border-radius: 10px;
                padding: 8px;
                font-size: 18px;
                color: #1F3D2B;
            }
            QPushButton {
                background-color: #F8BBD0;
                color: #4A2030;
                border: 2px solid #F48FB1;
                border-radius: 14px;
                padding: 11px 24px;
                font-size: 18px;
                font-weight: bold;
                min-width: 135px;
                min-height: 42px;
            }
            QPushButton:hover {
                background-color: #F48FB1;
            }
            QPushButton:pressed {
                background-color: #EC407A;
                color: white;
            }
        """)
        
        #Podesavanja layouta
        
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(45, 28, 45, 28)

        title_label = QLabel("MONITOR DRŽANJA KIČME")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 38px;
                font-weight: 800;
                color: #2D6A4F;
                padding: 8px;
            }
        """)
        main_layout.addWidget(title_label)

        
        # Unosi korisnika
        
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 2px solid #D8F3DC;
                border-radius: 18px;
                padding: 12px;
            }
        """)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(24)
        input_layout.setAlignment(Qt.AlignCenter)

        threshold_box = QVBoxLayout()
        threshold_label = QLabel("Prag ugla [°]")
        threshold_label.setAlignment(Qt.AlignCenter)
        threshold_label.setStyleSheet("font-weight: bold; color: #2D6A4F;")

        self.threshold_input = QLineEdit()
        self.threshold_input.setPlaceholderText("Unesi prag")
        self.threshold_input.setAlignment(Qt.AlignCenter)
        self.threshold_input.setFixedWidth(135)
        self.threshold_input.setEnabled(False)
        self.threshold_input.setAlignment(Qt.AlignCenter)
        self.threshold_input.setFixedWidth(135)

        threshold_box.addWidget(threshold_label)
        threshold_box.addWidget(self.threshold_input)

        time_box = QVBoxLayout()
        time_label = QLabel("Min. vreme [s]")
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setStyleSheet("font-weight: bold; color: #2D6A4F;")

        self.min_bad_time_input = QLineEdit()
        self.min_bad_time_input.setPlaceholderText("Unesi vreme")
        self.min_bad_time_input.setAlignment(Qt.AlignCenter)
        self.min_bad_time_input.setFixedWidth(135)
        self.min_bad_time_input.setEnabled(False)
        self.min_bad_time_input.setAlignment(Qt.AlignCenter)
        self.min_bad_time_input.setFixedWidth(135)

        time_box.addWidget(time_label)
        time_box.addWidget(self.min_bad_time_input)

        input_layout.addLayout(threshold_box)
        input_layout.addLayout(time_box)

        input_frame.setLayout(input_layout)
        main_layout.addWidget(input_frame, alignment=Qt.AlignCenter)

        
        # Dugmad
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(18)
        button_layout.setAlignment(Qt.AlignCenter)

        self.start_button = QPushButton("START")
        self.stop_button = QPushButton("STOP")
        self.confirm_button = QPushButton("POTVRDI")
       
        self.confirm_button.setEnabled(False)
       
        # Kliknuta dugmad menjanju stanje aplikacije
        
        self.start_button.clicked.connect(self.start_application) #start
        self.stop_button.clicked.connect(self.stop_application) #stop
        self.confirm_button.clicked.connect(self.confirm_settings) #potvrdi
       
        # dodavanje dugmadi 
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.confirm_button)


        main_layout.addLayout(button_layout)

        
        # GIF : ) ***
        
        self.gif_label = QLabel()
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setFixedSize(340, 280)
        self.gif_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #B7E4C7;
                border-radius: 22px;
                color: #2D6A4F;
                font-size: 22px;
                font-weight: bold;
            }
        """)
        
        

        try:
            current_folder = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            current_folder = os.getcwd()

        gif_path = os.path.join(current_folder, "bad_posture.gif")

        self.movie = QMovie(gif_path)

        if self.movie.isValid():
            self.movie.setScaledSize(QSize(390, 250))
            self.gif_label.setMovie(self.movie)
            self.movie.start()
        else:
            self.gif_label.setText("GIF bad_posture.gif\nnije pronađen")

        main_layout.addWidget(self.gif_label, alignment=Qt.AlignCenter)

        # ***
        
        
        
        
        # Obavestenje za korisnika o trenutnom stanju
        self.state_label = QLabel("Spremno, pritisnite start")
        self.state_label.setAlignment(Qt.AlignCenter)
        
        #Stylesheet za obavestenje
        self.state_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 800;
                color: #2D6A4F;
                background-color: #D8F3DC;
                border-radius: 16px;
                padding: 11px 35px;
            }
        """)
        main_layout.addWidget(self.state_label, alignment=Qt.AlignCenter)

        
        # Podaci 
    
        data_frame = QFrame()
        data_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #D8F3DC;
                border-radius: 18px;
                padding: 14px;
            }
        """)

        data_layout = QVBoxLayout()
        data_layout.setSpacing(10)

        row1 = QHBoxLayout()
        row1.setSpacing(18)
        row1.setAlignment(Qt.AlignCenter)

        self.ax_label = QLabel("ax = 0.00 m/s²")
        self.ay_label = QLabel("ay = 0.00 m/s²")
        self.az_label = QLabel("az = 0.00 m/s²")
        self.angle_label = QLabel("ugao = 0.00°")

        for label in [self.ax_label, self.ay_label, self.az_label, self.angle_label]:
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    font-size: 19px;
                    font-weight: bold;
                    background-color: #FCE4EC;
                    border-radius: 12px;
                    padding: 9px 15px;
                    min-width: 135px;
                }
            """)
            row1.addWidget(label)

        self.calibration_label = QLabel(
            "Kalibracija: axcal=0.00, aycal=0.00, azcal=9.81"
        )
        self.calibration_label.setAlignment(Qt.AlignCenter)
        self.calibration_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #2D6A4F;
                font-weight: bold;
            }
        """)

        row2 = QHBoxLayout()
        row2.setSpacing(18)
        row2.setAlignment(Qt.AlignCenter)

        self.violation_label = QLabel("Prekršaji: 0")
        self.bad_time_label = QLabel("Loše vreme: 0.0 s")

        for label in [self.violation_label, self.bad_time_label]:
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    font-size: 19px;
                    font-weight: bold;
                    background-color: #E9F8EC;
                    border-radius: 12px;
                    padding: 9px 15px;
                    min-width: 190px;
                }
            """)
            row2.addWidget(label)

        data_layout.addLayout(row1)
        data_layout.addWidget(self.calibration_label)
        data_layout.addLayout(row2)

        data_frame.setLayout(data_layout)
        main_layout.addWidget(data_frame, alignment=Qt.AlignCenter)

        self.setLayout(main_layout)
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    
    # START 
    
    def start_application(self):
        
        # Provera da li je  ispravan port,
        # i ako je port vec otvoren, ignorisemo ponovni klik na START
        if self.serial_port is not None and self.serial_port.is_open:
            return

        try:
            # Koristimo port definisan u __init__
            self.serial_port = serial.Serial(self.serial_port_name, 9600, timeout=0.05)
            time.sleep(2)
            #Dodato vreme za pokretanje arduina
          
        
        #Error handling za port...
        except Exception as error:
            QMessageBox.critical(
                self,
                "Greška",
                f"Ne mogu da otvorim serijski port '{self.serial_port_name}'.\n\n{error}"
            )
            self.serial_port = None
            return
        
        # Resetovanje vrednosti
        self.reset_session_variables()
        
        # Saljemo komandu arduinu START, pocinje akvizicija podataka
        self.send_command("START")

        #Prelazimo u naredno stanje, ceka dodir tastera
        self.state = "WAIT_CALIBRATION_TOUCH"
        
        self.is_reading = True # Dozvoljavamo rad pozadinske niti
        # Kreiranje i pokretanje pozadinske niti preko standardnog 'threading' modula
        # daemon=True osigurava da se nit automatski gasi kada se zatvori glavni prozor aplikacije
        self.read_thread = threading.Thread(target=self.serial_read_thread, daemon=True)
        self.read_thread.start()

        self.update_gui() # Vizuelno refreshovanje ekrana

#...............................................................................................
    
    # STOP
    
    def stop_application(self):
        self.stop_session(save_file=True)
        # Zaustavljenaje aplikacije preko pomocne funkcije i cuvanje rezultata u fajl

    def stop_session(self, save_file):
        self.is_reading = False # Zaustavlja while petlju u pozadinskoj niti

        if self.serial_port is not None and self.serial_port.is_open:
            try:
                self.send_command("LED:0") #gasi led
                self.send_command("STOP") #prelaz u stanje stop
                time.sleep(0.1) # vreme za ucitavanje arduina
                self.serial_port.close() #zatvaramo serijski port
            except Exception:
                pass

        self.serial_port = None
        self.state = "STOP"
        self.led_state = 0

        if save_file: #cuvanje fajla
            self.save_results()
            QMessageBox.information(
                self, #poruka za korisnika
                "Kraj rada",
                "Rezultati su sačuvani u fajl monitor_drzanja.txt"
            )

        self.update_gui() #osvezavanje
        
# ***************************************************************************        

    # Resetovanje promenljivih, self explanatory...
    
    def reset_session_variables(self):
        self.ax = 0.0
        self.ay = 0.0
        self.az = 0.0
        self.angle = 0.0

        self.ax_cal = 0.0
        self.ay_cal = 0.0
        self.az_cal = 9.81 

        self.calibration_samples = []
        self.calibration_start_time = None

        self.test_start_time = None
        self.max_test_angle = 0.0

        self.violation_count = 0
        self.total_bad_time = 0.0
        self.continuous_bad_time = 0.0
        self.was_bad = False

        self.last_sample_time = None
        self.led_state = 0

        self.send_command("LED:0")
        self.send_command("DISP:0")
        self.threshold_deg = None
        self.min_bad_time_sec = None
        
        self.threshold_input.clear()
        self.min_bad_time_input.clear()
        
        self.threshold_input.setEnabled(False)
        self.min_bad_time_input.setEnabled(False)
        self.confirm_button.setEnabled(False)

    #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    
    # SERIJSKA KOMUNIKACIJA I NITI
    #Slanje komandi na hardver, pomocna funkcija
    def send_command(self, command):
        if self.serial_port is None or not self.serial_port.is_open:
            return
        try:
            # Komandi dodajemo oznaku za novi red '\n', pretvaramo je u bajtove (encode) i šaljemo
            self.serial_port.write((command + "\n").encode())
        except Exception:
            pass

    # Citanje niti
    def serial_read_thread(self):
        # Beskonacna petlja niti koja osluškuje Arduino sve dok je self.is_reading == True
        while self.is_reading and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0: # Provera da li ima icega na liniji
                # Čitanje cele linije podataka, dekodiranje u string i uklanjanje '\r\n' karaktera
                    line = self.serial_port.readline().decode(errors="ignore").strip()
                    if line != "":
                        # slanje linije sa arduina na data received pyqt signal
                        self.data_received.emit(line)
                        
            except Exception as error:
                
                print(f"Prolazna greska u niti: {error}")
                
            time.sleep(0.01) #stiti od opterecivanja procesora
            
            
    #Procesuiranje linije koja je stigla s arduina
    
    def process_data_line(self, line):
        
        # Obradjuje tok podataka. Izvrsava se u glavnoj niti na svaki emitovan signal.
        if line.startswith("DATA"):
            #Parsira se linija koja je stigla sa arduina
            #Parse data line definisana ispod
            parsed = self.parse_data_line(line)
            if parsed is None:
                return
            
            self.ax, self.ay, self.az, touch = parsed
            current_time = time.time()
            
            #Pratimo vremenski razmak izmednju uzoraka kako bismo ga ako je potrebno
            #dodali u merenje ukupnog vremena u losem polozaju
            if self.last_sample_time is None:
                dt = 0.1
            else:
                dt = current_time - self.last_sample_time

            self.last_sample_time = current_time
            
            #Racunanje ugla, kasnije je definisana funkcija
            self.angle = self.calculate_angle(
                self.ax, self.ay, self.az,
                self.ax_cal, self.ay_cal, self.az_cal
            )
            
            #PROMENE STANJA
            #Na osnovu trenutnog stanja i informacija o dodiru iz arduina
            
            #Cekamo dodir da bismo presli u kalibraciju
            if self.state == "WAIT_CALIBRATION_TOUCH":
                if touch == 1:
                    self.state = "CALIBRATION"
                    self.calibration_samples = []
                    self.calibration_start_time = time.time()
                    
            #Vrsimo kalibraciju, funkcija je definisana kasnije
            elif self.state == "CALIBRATION":
                self.handle_calibration()
                
            #Kada je kalibracija zavrsena, ceka se dodir da bi pocelo testiranje
            elif self.state == "WAIT_TEST_TOUCH":
                if touch == 1:
                    self.state = "TESTING"
                    self.test_start_time = time.time()
                    self.max_test_angle = 0.0

            elif self.state == "TESTING":
                self.handle_testing()
                
            elif self.state == "WAIT_SETTINGS":
                pass
            
            elif self.state == "MONITORING":
                self.handle_monitoring(dt)

            self.update_gui()
        else:
            print("Arduino:", line)

    @staticmethod
    #Proverava da li je linija poslata na thread 
    #iz arduina ispravna i parsira je
    def parse_data_line(line):
        parts = line.split(",")

        if len(parts) != 5:
            return None

        try:
            ax_raw = float(parts[1])
            ay_raw = float(parts[2])
            az_raw = float(parts[3])
            touch = int(parts[4])
            
            # Konverzija  vrednosti u ubrzanje m/s^2 
            #Fomrula za konverziju je na osnovu kalibracije izvrsene u arduinu
            
            ax = -((ax_raw - 337.0) / 67.0) * 9.81
            ay = -((ay_raw - 337.0) / 67.0) * 9.81
            az = ((az_raw - 337.0) / 67.0) * 9.81
            
        except ValueError:
            return None

        return ax, ay, az, touch
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Pomocne staticke metode...
    
    
    #Funkcija koja racuna ugao izmedju trenutnog
    #i kalibrisanog polozaja na osnovu procitanih podataka iz akcelerometra
    @staticmethod
    def calculate_angle(ax, ay, az, ax_cal, ay_cal, az_cal):
        #Skalarni proizvod
        product = ax * ax_cal + ay * ay_cal + az * az_cal

        current_norm = math.sqrt(ax ** 2 + ay ** 2 + az ** 2)
        reference_norm = math.sqrt(ax_cal ** 2 + ay_cal ** 2 + az_cal ** 2)

        if current_norm == 0 or reference_norm == 0:
            return 0.0

        cos_value = product / (current_norm * reference_norm)
        cos_value = max(-1.0, min(1.0, cos_value))
     
        return math.degrees(math.acos(cos_value))
   #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 
    
    #IZVRSAVANJE KALIBRACIJE
    def handle_calibration(self):
        #Dodajemo procitana ubrzanja u listu iz koje cemo ih usrednjiti
        self.calibration_samples.append((self.ax, self.ay, self.az))
        #Merimo vreme, ona treba da traje 3s
        elapsed_time = time.time() - self.calibration_start_time
        #Kad istekne 3s, racuhnamo srednju vrednost
        if elapsed_time >= self.calibration_duration:
            n = len(self.calibration_samples)

            if n > 0:
                self.ax_cal = sum(sample[0] for sample in self.calibration_samples) / n
                self.ay_cal = sum(sample[1] for sample in self.calibration_samples) / n
                self.az_cal = sum(sample[2] for sample in self.calibration_samples) / n

            self.state = "WAIT_TEST_TOUCH"

#...........................................................................................

#TESTIRANJE
    def handle_testing(self):
        #Pratimo maksimalan ugao ostvaren tokom testiranja da bismo 
        #Obavestili korisnika o njemu na kraju testiranja
        if self.angle > self.max_test_angle:
            self.max_test_angle = self.angle
    
        elapsed_time = time.time() - self.test_start_time
    
        if elapsed_time >= self.test_duration:
            # Test od 8 s je završen.
            # Sada korisnik analizira ugao i unosi prag i minimalno vreme.
            self.state = "WAIT_SETTINGS"
            #Dozvoljen je unos pragova i ceka se potvrdjivanje unetog
            self.threshold_input.setEnabled(True)
            self.min_bad_time_input.setEnabled(True)
            self.confirm_button.setEnabled(True)
    
            self.violation_count = 0
            self.total_bad_time = 0.0
            self.continuous_bad_time = 0.0
            self.was_bad = False
            self.last_sample_time = None
    
            self.send_command("LED:0")
            self.send_command("DISP:0")
    #Potvrda da su uneti ispravni podaci
    def confirm_settings(self):
        try:
            threshold = float(self.threshold_input.text())
            min_bad_time = float(self.min_bad_time_input.text())
        except ValueError:
            QMessageBox.warning(
                self,
                "Neispravan unos",
                "Moraš uneti broj za prag ugla i broj za minimalno vreme."
            )
            return
    
        if threshold <= 0 or min_bad_time <= 0:
            QMessageBox.warning(
                self,
                "Neispravan unos",
                "Prag ugla i minimalno vreme moraju biti veći od nule."
            )
            return
    
        self.threshold_deg = threshold
        self.min_bad_time_sec = min_bad_time
    
        self.violation_count = 0
        self.total_bad_time = 0.0
        self.continuous_bad_time = 0.0
        self.was_bad = False
        self.last_sample_time = None
    
        self.send_command("LED:0")
        self.send_command("DISP:0")
    
        self.threshold_input.setEnabled(False)
        self.min_bad_time_input.setEnabled(False)
        self.confirm_button.setEnabled(False)
        
        self.state = "MONITORING"
        self.update_gui()
        
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    
    # ISPITIVANJE
    def handle_monitoring(self, dt):
        if self.threshold_deg is None or self.min_bad_time_sec is None:
            return
    
        threshold = self.threshold_deg
        min_bad_time = self.min_bad_time_sec
    
        is_bad = self.angle > threshold

        if is_bad:
            self.total_bad_time += dt
            self.continuous_bad_time += dt

            if not self.was_bad:
                self.violation_count += 1
                self.was_bad = True
                self.send_command(f"DISP:{self.violation_count}")

    # pali se lampica ako je predugo u nepravilnom polozaju
            if self.continuous_bad_time >= min_bad_time:
                self.set_led_state(1)
            else:
                self.set_led_state(0)

        else:
            self.continuous_bad_time = 0.0
            self.was_bad = False
            self.set_led_state(0)
            
    #Menjanje stanja diode
    def set_led_state(self, new_state):
        if self.led_state == new_state:
            return

        self.led_state = new_state

        if new_state == 1:
            self.send_command("LED:1")
        else:
            self.send_command("LED:0")
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#UPDATE Interfejsa
    def update_gui(self):
        #   Obavestenje o trenutnom stanju 
        
        state_text = {
            "IDLE": "Spremno",
            "WAIT_CALIBRATION_TOUCH": "Dodirni senzor za kalibraciju",
            "CALIBRATION": "Kalibracija...",
            "WAIT_TEST_TOUCH": "Dodirni senzor za test",
            "TESTING": "Testiranje...",
            "WAIT_SETTINGS": f"Maksimalni ugao nagiba: {self.max_test_angle:.1f} stepeni. \
                \nUnesi prag i vreme i potvrdi",
            "MONITORING": "Aktivan nadzor",
            "STOP": "Program je zaustavljen"
        }

        self.state_label.setText(state_text.get(self.state, self.state))

        self.ax_label.setText(f"ax = {self.ax:.2f} m/s²")
        self.ay_label.setText(f"ay = {self.ay:.2f} m/s²")
        self.az_label.setText(f"az = {self.az:.2f} m/s²")
        self.angle_label.setText(f"ugao = {self.angle:.2f}°")

        self.calibration_label.setText(
            f"Kalibracija: axcal={self.ax_cal:.2f} m/s², "
            f"aycal={self.ay_cal:.2f} m/s², azcal={self.az_cal:.2f} m/s²"
        )

        self.violation_label.setText(f"Prekršaji: {self.violation_count}")
        self.bad_time_label.setText(f"Loše vreme: {self.total_bad_time:.1f} s")

  #UPIS U FAJL
   
    def save_results(self):
        with open("monitor_drzanja.txt", "w", encoding="utf-8") as file:
            file.write("Rezultati sesije\n")
            file.write(f"axcal = {self.ax_cal:.4f} m/s²\n")
            file.write(f"aycal = {self.ay_cal:.4f} m/s²\n")
            file.write(f"azcal = {self.az_cal:.4f} m/s²\n")
            file.write(f"Ukupan broj prekršaja = {self.violation_count}\n")
            file.write(f"Ukupno vreme u lošem položaju = {self.total_bad_time:.1f} s\n")

    def closeEvent(self, event):
        self.stop_session(save_file=False)
        event.accept()


app = QApplication.instance()

if app is None:
    app = QApplication(sys.argv)

window = PostureMonitor()
window.show()

app.exec_()