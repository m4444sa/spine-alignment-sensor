#include <TimerOne.h>
#include <TM1637Display.h>

//Definisanje pinova

#define CLK_PIN 9
#define DIO_PIN 8

#define TOUCH_PIN 2

#define X_PIN A0
#define Y_PIN A1
#define Z_PIN A2

#define LED_PIN 13   // ugradjena LED dioda na Arduinu

// TM1637 displej

TM1637Display display(CLK_PIN, DIO_PIN);

volatile bool timerFlag = false;
volatile bool touchFlag = false;

bool acquisitionEnabled = false;   // da li Arduino trenutno salje podatke
bool currentTouchValue = false;    

// Debaunisanje :
// Pretpostavka: dodiri koji se dese u razmaku manjem od 300 ms
// smatraju se istim fizičkim dodirom.
unsigned long lastTouchTime = 0;   
const unsigned long touchDebounceTime = 300; 

int displayValue = 0;

//Interrupt Service Routines

// 1) TimerISR se poziva svakih 100 ms i menja flag 
void timerIsr() {
  timerFlag = true;
}

// 2) TouchISR se pali na dodir senzora
void touchIsr() {
  touchFlag = true;
}

//Setup :

void setup() {
  Serial.begin(9600);

  Serial.setTimeout(5);

  pinMode(LED_PIN, OUTPUT);
  pinMode(TOUCH_PIN, INPUT);

  digitalWrite(LED_PIN, LOW);

  display.setBrightness(0x0f);
  display.showNumberDec(0, false);

  // Interrupt za kapacitivni senzor dodira, pin D2
  attachInterrupt(digitalPinToInterrupt(TOUCH_PIN), touchIsr, RISING);

  // 100 ms = 100000 us
  Timer1.initialize(100000);
  Timer1.attachInterrupt(timerIsr);

  Serial.println("READY");
  Serial.println("Komande: START, STOP, LED:1, LED:0, DISP:broj, RESET");
}


// Loop :

void loop() {
  receiveCommandFromPython();
  processTouch();

  if (timerFlag) {
    
    timerFlag = false;
    
    //slanje podataka pythonu...
    if (acquisitionEnabled) {
      sendSensorDataToPython();
    }
  }
}

// Obrada dodira

void processTouch() {
  if (!touchFlag) {
    return;
  }

  touchFlag = false;

  unsigned long currentTime = millis();

  if (currentTime - lastTouchTime > touchDebounceTime) {
    currentTouchValue = true;
    lastTouchTime = currentTime;
  }
}

// Slanje podataka Python-u
// DATA,x,y,z,touch

void sendSensorDataToPython() {
  int x_val = analogRead(X_PIN);
  int y_val = analogRead(Y_PIN);
  int z_val = analogRead(Z_PIN);

  Serial.print("DATA,");
  Serial.print(x_val);
  Serial.print(",");
  Serial.print(y_val);
  Serial.print(",");
  Serial.print(z_val);
  Serial.print(",");

  if (currentTouchValue) {
    Serial.println("1");
    currentTouchValue = false;  // dodir je prijavljen Python-u
  } else {
    Serial.println("0");
  }
}


// Prijem komandi iz Python-a
//
// Komande i sta rade:
// START       -> pocinje slanje podataka
// STOP        -> prestaje slanje podataka
// LED:1       -> pali LED
// LED:0       -> gasi LED
// DISP:5      -> prikazuje broj 5 na displeju
// RESET       -> resetuje LED, displej i touch flag

void receiveCommandFromPython() {
  if (Serial.available() <= 0) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "START") {
    acquisitionEnabled = true;
    currentTouchValue = false;

    Serial.println("START");
  }

  else if (command == "STOP") {
    acquisitionEnabled = false;

    digitalWrite(LED_PIN, LOW);
    Serial.println("STOP");
  }

  else if (command == "RESET") {
    acquisitionEnabled = false;

    digitalWrite(LED_PIN, LOW);
    displayValue = 0;
    display.showNumberDec(displayValue, false);

    currentTouchValue = false;

    Serial.println("RESET");
  }

  else if (command.startsWith("LED:")) {
    int ledState = command.substring(4).toInt();

    if (ledState == 1) {
      digitalWrite(LED_PIN, HIGH);
      Serial.println("LED:1");
    } else {
      digitalWrite(LED_PIN, LOW);
      Serial.println("LED:0");
    }
  }

  else if (command.startsWith("DISP:")) {
    displayValue = command.substring(5).toInt();

// podesavanje displeja
    if (displayValue < 0) {
      displayValue = 0;
    }

    if (displayValue > 9999) {
      displayValue = 9999;
    }

    display.showNumberDec(displayValue, false);
    Serial.print("DISP:");
    Serial.println(displayValue);
  }
// za nepoznatu komandu ->
  else {
    Serial.print("ERR,UNKNOWN_COMMAND:");
    Serial.println(command);
  }
}