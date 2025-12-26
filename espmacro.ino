// Safe ESP32 GPIO Pin Definitions

#include <DHT.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>
#include <Wire.h>

#define CLK 18         // Rotary encoder CLK pin
#define DT 19          // Rotary encoder DT pin
#define SW 21          // Rotary encoder pushbutton

#define DHTPIN 33        // Use any free digital GPIO
#define DHTTYPE DHT22    // or DHT11 if that's what you have

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_SDA 22
#define OLED_SCL 23

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

#define buttonOnePin 13
#define buttonTwoPin 12
#define buttonThreePin 14
#define buttonFourPin 25
#define buttonFivePin 26
#define buttonSixPin 27

int lastStateCLK;
int counter = 0;
int oldCounter = 0;
unsigned long previousMillis = 0;
unsigned long interval = 15 * 60 * 1000UL;

enum ButtonEvent { None, SingleClick, DoubleClick, LongPress };
const unsigned long ButTimeout    = 250; 
const unsigned long LongPressTime = 1000; 
const unsigned long debounceDelay = 10; 
DHT dht(DHTPIN, DHTTYPE);

struct ButtonState {
  byte stableState;          
  byte lastReading;          
  unsigned long lastDebounceTime; 
  unsigned long pressTime;  
  unsigned long msecLst;     
  bool longPressReported;   
};

ButtonState buttonOneState   = { HIGH, HIGH, 0, 0, 0, false };
ButtonState buttonTwoState   = { HIGH, HIGH, 0, 0, 0, false };
ButtonState buttonThreeState = { HIGH, HIGH, 0, 0, 0, false };
ButtonState buttonFourState  = { HIGH, HIGH, 0, 0, 0, false };
ButtonState buttonFiveState  = { HIGH, HIGH, 0, 0, 0, false };
ButtonState buttonSixState   = { HIGH, HIGH, 0, 0, 0, false };

void setup() {
  pinMode(CLK, INPUT_PULLUP);
  pinMode(DT, INPUT_PULLUP);
  pinMode(SW, INPUT_PULLUP);

  pinMode(buttonOnePin,   INPUT_PULLUP);
  pinMode(buttonTwoPin,   INPUT_PULLUP);
  pinMode(buttonThreePin, INPUT_PULLUP);
  pinMode(buttonFourPin,  INPUT_PULLUP);
  pinMode(buttonFivePin,  INPUT_PULLUP);
  pinMode(buttonSixPin,   INPUT_PULLUP);

  Serial.begin(115200);
  dht.begin();
  lastStateCLK = digitalRead(CLK);
}

void loop() {
  unsigned long now = millis();

  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= interval) {
    OledTemp();
    previousMillis = currentMillis;
  }
  volumeRotary();
  buttonPressCheckWrapper(buttonOnePin,   now, buttonOneState,   "buttonOne");
  buttonPressCheckWrapper(buttonTwoPin,   now, buttonTwoState,   "buttonTwo");
  buttonPressCheckWrapper(buttonThreePin, now, buttonThreeState, "buttonThree");
  buttonPressCheckWrapper(buttonFourPin,  now, buttonFourState,  "buttonFour");
  buttonPressCheckWrapper(buttonFivePin,  now, buttonFiveState,  "buttonFive");
  buttonPressCheckWrapper(buttonSixPin,   now, buttonSixState,   "buttonSix");
}

void volumeRotary() {
  int currentStateCLK = digitalRead(CLK);
  if (currentStateCLK != lastStateCLK) {
    if (digitalRead(DT) != currentStateCLK) {
      counter--; 
    } else {
      counter++; 
    }
    Serial.print("Counter: ");
    Serial.println(counter);
    if (counter > oldCounter) {
      Serial.println("UP");
    } else if (counter < oldCounter) {
      Serial.println("DOWN");
    }
    oldCounter = counter;
  }
  lastStateCLK = currentStateCLK;

  if (digitalRead(21) == LOW) { 
    Serial.println("MUTE");
    delay(1000); 
  }
}

int buttonPressCheck(int buttonPin, unsigned long now, ButtonState &state) {
  byte reading = digitalRead(buttonPin);

  if (reading != state.lastReading) {
    state.lastDebounceTime = now;
  }
  state.lastReading = reading;

  if ((now - state.lastDebounceTime) > debounceDelay) {
    if (reading != state.stableState) {
      state.stableState = reading;
      if (state.stableState == LOW) {
        // Button pressed
        state.pressTime = now;
        state.longPressReported = false;
      } else {
        unsigned long pressDuration = now - state.pressTime;
        if (pressDuration >= LongPressTime && !state.longPressReported) {
          state.longPressReported = true;
          state.msecLst = 0;
          return LongPress;
        }
        else if (!state.longPressReported) {
          if (state.msecLst != 0 && (now - state.msecLst < ButTimeout)) {
            state.msecLst = 0;
            return DoubleClick;
          }
          else {
            state.msecLst = now;
          }
        }
      }
    }
  }

  if (state.msecLst != 0 && (now - state.msecLst > ButTimeout)) {
    state.msecLst = 0;
    return SingleClick;
  }

  if (state.stableState == LOW && !state.longPressReported && (now - state.pressTime >= LongPressTime)) {
    state.longPressReported = true;
    state.msecLst = 0;
    return LongPress;
  }

  return None; 
}

void OledTemp()
{
  Wire.begin(OLED_SDA, OLED_SCL);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();

  float temp = dht.readTemperature();
  float hum = dht.readHumidity();

  if (isnan(temp) || isnan(hum)) {
    Serial.println("Failed to read from DHT sensor!");
    scrollText("Failed to read from DHT sensor!", 3);
    return;
  }
  else
  {
    scrollText("Temp: " + String(temp) + " C & Humidity: " + String(hum) + "%" , 2);
    int aInt = (int)(temp * 100);  // 12.34 → 1234
    int bInt = (int)(hum * 100);  // 56.78 → 5678
    long combined = (long)aInt * 10000 + bInt;
    Serial.println((combined)); 
  }
}

void scrollText(String text, uint8_t textSize) {
  int16_t x = display.width();  // Start off right edge
  int16_t y = (display.height() / 2) - (textSize * 8);  // Center vertically
  
  display.setTextSize(textSize);
  display.setTextColor(WHITE);
  
  while (x > -display.width()) {  // Scroll until text exits left
    display.clearDisplay();
    display.setCursor(x, y);
    display.print(text);
    display.display();
    x -= 2;  // Adjust speed here
    delay(20);  // Adjust smoothness here
  }
    display.clearDisplay();
    display.display();
}
 
void buttonPressCheckWrapper(int buttonPin, unsigned long now, ButtonState &state, const char* buttonName) {
  int event = buttonPressCheck(buttonPin, now, state);
  switch (event) {
    case SingleClick:
      Serial.print(buttonName);
      Serial.print("SingleClick");
      Serial.println();
      break;
    case DoubleClick:
      if(buttonName == "buttonFive")
      {
          OledTemp();
          break;
      }
      Serial.print(buttonName);
      Serial.print("DoubleClick");
      Serial.println();
      break;
    case LongPress:
      if(buttonName == "buttonFive")
      {
          OledTemp();
          break;
      }
      Serial.print(buttonName);
      Serial.print("LongPress");
      if(buttonName == "buttonTwo")
        scrollText("looooooooooooooooping",2);
      Serial.println();
      break;
    default:
      break;
  }
}
