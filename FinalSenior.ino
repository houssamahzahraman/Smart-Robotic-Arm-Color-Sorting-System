
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>
#include <math.h>

//const char* ssid     = "Rahaf";
//const char* password = "03498210$";
const char* ssid     = "Ahmad";
const char* password = "03498210$";
//
//const char* ssid     = "Ahmad's iPhone";
//const char* password = "123456789";
//const char* ssid     = "Hussam";
//const char* password = "1020304050";

//const char* ssid     = "BoB-Net-abdalla-70 12 20 14";
//const char* password = "20062006";
//const char* ssid     = "OK";
//const char* password = "99999999";

ESP8266WebServer server(80);
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// ── Link lengths ──
float L1 = 9.5;
float L2 = 10.5;
float L3 = 9.5;
float L4 = 14.5;

int minPulse = 130;
int maxPulse = 530;

int homePos[6] = {370, 360, 200, 320, 180, 320};
int current[6] = {370, 360, 200, 320, 180, 320};

// ── Box positions ──
int redBox[6]   = {340, 360, 250, 320, 250, 330}; 
int greenBox[6] = {300, 360, 250, 320, 250, 300};
int blueBox[6]  = {240, 360, 250, 320, 250, 300};

// ── Stats ──
int redCount   = 0;
int blueCount  = 0;
int greenCount = 0;
String armStatus = "IDLE";

// ── Flags ──
bool isBusy      = false;
bool shouldMove  = false;
bool started     = false;
float target_x   = 0;
float target_y   = 0;
String target_color = "";

// ════════════════════════════════
// MOVEMENT
// ════════════════════════════════

void moveSmooth(int ch, int target) {
  target = constrain(target, minPulse, maxPulse);
  while (current[ch] != target) {
    if (current[ch] < target) current[ch] += 2;
    else                       current[ch]--;
    pwm.setPWM(ch, 0, current[ch]);
    delay(10);
    server.handleClient();
  }
}

void goHome() {
  Serial.println("Going home...");
  armStatus = "HOME";
  moveSmooth(1, 360);
  for (int i = 0; i < 6; i++) {
    moveSmooth(i, homePos[i]);
    delay(100);
  }
  armStatus = "IDLE";
  Serial.println("Home reached!");
}

//void goToBox(int boxPos[]) {
//  for (int i = 0; i < 6; i++) {
//    moveSmooth(i, boxPos[i]);
//    delay(100);
//  }
//}
void goToBox(int boxPos[]) {
  moveSmooth(0, boxPos[0]);
  moveSmooth(5, boxPos[5]);

  
  moveSmooth(4, boxPos[4]);
}

int toPWM(float deg, bool reversed) {
  deg = constrain(deg, 0, 180);
  if (reversed)
    return map((int)deg, 0, 180, maxPulse, minPulse);
  else
    return map((int)deg, 0, 180, minPulse, maxPulse);
}

// ════════════════════════════════
// IK
// ════════════════════════════════
// حساب الزوايا
void moveToXY(float tx, float ty) {
  tx = -1 * tx - 10 + 1;
  ty = ty + 3 - 1;

  Serial.println("─────────────────");
  Serial.print("Target: x="); Serial.print(tx);
  Serial.print("  y="); Serial.println(ty);

  // 0 - Base
  float baseDeg = atan2(ty, tx) * 180.0 / PI + 10;
  if (baseDeg < 0) baseDeg += 180.0;
 
  int basePWM = toPWM(baseDeg, false);
  Serial.print("Base="); Serial.print(baseDeg);
  Serial.print("° PWM="); Serial.println(basePWM);
  moveSmooth(0, basePWM);
  delay(500);

  // Distances
  float r   = sqrt(tx*tx + ty*ty);
  float z   = -L1;
  float D   = sqrt(r*r + z*z);
  float L34 = L3 + L4;

  Serial.print("r="); Serial.print(r);
  Serial.print(" D="); Serial.println(D);

  if (D > L2 + L34) { Serial.println("Too far!"); return; }
  if (D < abs(L2 - L34)) { Serial.println("Too close!"); return; }

  // Shoulder + Elbows
  float cosTheta2 = (D*D - L2*L2 - L34*L34) / (2.0 * L2 * L34);
  cosTheta2 = constrain(cosTheta2, -1.0, 1.0);
  float theta2 = acos(cosTheta2);

  float alpha = atan2(-z, r);
  float beta  = atan2(L34 * sin(theta2), L2 + L34 * cos(theta2));
  float sDeg  = (alpha - beta) * 180.0 / PI;
  if (sDeg < 0) sDeg += 180.0;

  float totalElbowDeg = theta2 * 180.0 / PI;
  float e1Deg = totalElbowDeg / 2.0;
  float e2Deg = totalElbowDeg / 2.0;

  int shoulderPWM = toPWM(sDeg,  true);
  int elbow1PWM   = toPWM(e1Deg, false);
  int elbow2PWM   = toPWM(e2Deg, false);

  Serial.print("Shoulder="); Serial.print(sDeg);
  Serial.print("° E1="); Serial.print(e1Deg);
  Serial.print("° E2="); Serial.println(e2Deg);

  moveSmooth(1, 350);
  moveSmooth(2, elbow1PWM);
  moveSmooth(5, elbow2PWM);
  moveSmooth(1, shoulderPWM);
  moveSmooth(4, 400); // امسك
  delay(400);
  moveSmooth(1, 350); // ارتفع
  moveSmooth(2, 200);

  Serial.println("Done!");
}

// ════════════════════════════════
// SORT CYCLE
// ════════════════════════════════

void sortCycle(float tx, float ty, String color) {
  isBusy   = true;
  armStatus = "CATCHING";
  Serial.println("Sorting: " + color);

  // 1. روح على موقع المكعب
  moveToXY(tx, ty);
  delay(300);

  // 2. روح للصندوق المناسب
  armStatus = "MOVING TO BOX";
  if      (color == "RED")   { goToBox(redBox);   redCount++;   }
  else if (color == "GREEN") { goToBox(greenBox); greenCount++; }
  else if (color == "BLUE")  { goToBox(blueBox);  blueCount++;  }

  delay(300);

  // 3. اترك المكعب
  moveSmooth(4, 200);
  delay(300);

  // 4. ارجع للهوم
  goHome();

  isBusy   = false;
  armStatus = "IDLE";
  Serial.println("Cycle complete!");
}

// ════════════════════════════════
// CORS
// ════════════════════════════════

void setCORS() {
  server.sendHeader("Access-Control-Allow-Origin",  "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}

void handleOptions() {
  setCORS();
  server.send(204);
}

// ════════════════════════════════
// ROUTES
// ════════════════════════════════

void handleData() {
  setCORS();
  String json = "{";
  json += "\"red\":"   + String(redCount)   + ",";
  json += "\"green\":" + String(greenCount) + ",";
  json += "\"blue\":"  + String(blueCount)  + ",";
  json += "\"total\":" + String(redCount + blueCount + greenCount) + ",";
  json += "\"status\":\"" + armStatus + "\"";
  json += "}";
  server.send(200, "application/json", json);
}

void handlePosition() {
  setCORS();
  if (isBusy) { server.send(503, "text/plain", "BUSY"); return; }

  if (server.hasArg("plain")) {
    StaticJsonDocument<128> doc;
    deserializeJson(doc, server.arg("plain"));

    target_color = doc["color"].as<String>();
    target_x     = doc["x"];
    target_y     = doc["y"];

    Serial.println("Got: " + target_color +
      " x=" + String(target_x) +
      " y=" + String(target_y));

    server.send(200, "text/plain", "OK");
    shouldMove = true;
  }
}

void handleControl() {
  setCORS();
  if (isBusy) { server.send(503, "text/plain", "BUSY"); return; }

  if (server.hasArg("plain")) {
    StaticJsonDocument<64> doc;
    deserializeJson(doc, server.arg("plain"));
    String cmd = doc["cmd"];
    server.send(200, "text/plain", "OK");

    isBusy = true;
    if      (cmd == "RED")   { goToBox(redBox);   goHome(); }
    else if (cmd == "GREEN") { goToBox(greenBox); goHome(); }
    else if (cmd == "BLUE")  { goToBox(blueBox);  goHome(); }
    else if (cmd == "HOME")  goHome();
    isBusy = false;
  }
}

void handleServo() {
  setCORS();
  if (server.hasArg("plain")) {
    StaticJsonDocument<64> doc;
    deserializeJson(doc, server.arg("plain"));
    int id  = doc["id"];
    int val = constrain((int)doc["value"], minPulse, maxPulse);
    current[id] = val;
    pwm.setPWM(id, 0, val);
    server.send(200, "text/plain", "OK");
  }
}

// ════════════════════════════════
// SETUP & LOOP
// ════════════════════════════════

void setup() {
  Serial.begin(115200);
  Wire.begin(D2, D1);
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(1000);

  WiFi.begin(ssid, password);
  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nConnected! IP: " + WiFi.localIP().toString());

  server.on("/data",     HTTP_GET,     handleData);
  server.on("/position", HTTP_POST,    handlePosition);
  server.on("/position", HTTP_OPTIONS, handleOptions);
  server.on("/control",  HTTP_POST,    handleControl);
  server.on("/control",  HTTP_OPTIONS, handleOptions);
  server.on("/servo",    HTTP_POST,    handleServo);
  server.on("/servo",    HTTP_OPTIONS, handleOptions);
  server.begin();
  Serial.println("Server ready!");
  pwm.setPWM(0, 0, 430);
}

void loop() {
  server.handleClient();

  if (!started) {
    goHome();
    Serial.println("Arm ready!");
    started = true;
  }

  if (shouldMove && !isBusy) {
    shouldMove = false;
    sortCycle(target_x, target_y, target_color);
  }
}
