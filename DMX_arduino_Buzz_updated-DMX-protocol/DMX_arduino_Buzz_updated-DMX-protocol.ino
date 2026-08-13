#include <DmxSimple.h>

int last_event = -1; // globale Variable, merkt sich das letzte Event

bool BuzzerLocked = false;

//neu:
bool connected = false;

unsigned long lastSerial = 0;



unsigned long Tastergedruecktzeit = 0;

int change_channel = 0;
int channelAdd = 0;

int B1_last = 0;
int B2_last = 0;
int B3_last = 0;

//Pins der LEDs in den Sockeln
int BuzzerlightRed_1 = 6;
int BuzzerlightRed_2 = 7;
int BuzzerlightRed_3 = 8;
int BuzzerlightGreen_1 = 9;
int BuzzerlightGreen_2 = 10;
int BuzzerlightGreen_3 = 11;
int BuzzerlightBlue_1 = 12;
int BuzzerlightBlue_2 = 13;
int BuzzerlightBlue_3 = A0;

//Pin des Pedals
int ModeratorPedal = A1;
int ModeratorPedalState = 0;
int LastPedal = 0;

//Pins und states der Buzzer
int Buzzer_1 = 3;
int Buzzerstate_1 = 0;
int Buzzer_2 = 4;
int Buzzerstate_2 = 0;
int Buzzer_3 = 5;
int Buzzerstate_3 = 0;

int DMX_CH = 0;
int DMX_Value = 0;

bool Lock_QUIZDMX = false;

int current_event = 0;
int wait_for_response_connection = 0;
String c = "";
void setup() {
  Serial.begin(115200);
  //lampe reset
  DmxSimple.usePin(2); //digital output für DMX - serielle daten
  DmxSimple.write(1, 255);
  DmxSimple.write(31, 0);
  DmxSimple.write(33, 0);
  DmxSimple.write(37, 255);

  //Pinmodes:
  pinMode(BuzzerlightRed_1, OUTPUT);
  pinMode(BuzzerlightRed_2, OUTPUT);
  pinMode(BuzzerlightRed_3, OUTPUT);

  pinMode(BuzzerlightGreen_1, OUTPUT);
  pinMode(BuzzerlightGreen_2, OUTPUT);
  pinMode(BuzzerlightGreen_3, OUTPUT);

  pinMode(BuzzerlightBlue_1, OUTPUT);
  pinMode(BuzzerlightBlue_2, OUTPUT);
  pinMode(BuzzerlightBlue_3, OUTPUT);
  
  pinMode(Buzzer_1, INPUT);
  pinMode(Buzzer_2, INPUT);
  pinMode(Buzzer_3, INPUT);

  pinMode(ModeratorPedal, INPUT);


  //warte bis python das OK gibt:
  while (!Serial);
    Serial.println("Arduino bereit");
  //alle lichter aus:
  reset_Buzzlights();
}

void loop() {

  // warten bis PC verbindet
  if(!connected){

    Serial.println(
      "I'm waiting for response: Quizconsole for Buzz"
    );


    delay(500);


    if(Serial.available()){

      String s = Serial.readStringUntil('\n');
      s.trim();


      if(s == "1"){

        connected = true;
        lastSerial = millis();

        Serial.println("CONNECTED");

        Reset();

      }

    }


    return;

  }



  // normale Kommunikation
  if(Serial.available()){


    String s = Serial.readStringUntil('\n');

    s.trim();


    lastSerial = millis();



    if(s.startsWith("E")){


      current_event =
        s.substring(1).toInt();


      Lock_QUIZDMX=false;


    }


    else if(s.startsWith("D;")){


      int first = s.indexOf(';');
      int second = s.indexOf(';', first+1);


      int ch =
        s.substring(first+1,second).toInt();


      int val =
        s.substring(second+1).toInt();


      DmxSimple.write(
        ch,
        val
      );


      Lock_QUIZDMX=true;


    }


    else if(s.startsWith("S;")){


      applyScene(s);


    }


    else if(s=="C"){

      clearDMX();

    }


  }


  // hier kommt dein Quizcode weiter...




  ModeratorPedalState = digitalRead(ModeratorPedal);
  if (ModeratorPedalState == HIGH) {
    if (Tastergedruecktzeit == 0) {
        Tastergedruecktzeit = millis();
      }
      else {
        if (millis() - Tastergedruecktzeit >= 5000) {
          change_channels();
          Tastergedruecktzeit = 0;
        }
      }
    }
    else {
      if (Tastergedruecktzeit != 0) {
        Tastergedruecktzeit = 0;
      }
    }

  if (LastPedal != ModeratorPedalState) {
    if (ModeratorPedalState == HIGH) {
      Serial.println("Moderator_ENTER");
    }
    ModeratorPedalState = digitalRead(ModeratorPedal);
    LastPedal = ModeratorPedalState;
    delay(250);
  }


  //current_event = 2, Fragen & wer zuerst?
  if (current_event == 2) {
    Buzzerstate_1 = digitalRead(Buzzer_1);
    Buzzerstate_2 = digitalRead(Buzzer_2);
    Buzzerstate_3 = digitalRead(Buzzer_3);

    if (Buzzerstate_1 == HIGH && BuzzerLocked == false) {BuzzerLocked = true;Serial.println("Buzzer1");delay(250);}
    else if (Buzzerstate_2 == HIGH && BuzzerLocked == false) {BuzzerLocked = true;Serial.println("Buzzer2");delay(250);}
    else if (Buzzerstate_3 == HIGH && BuzzerLocked == false) {BuzzerLocked = true;Serial.println("Buzzer3");delay(250);}
  }

  //wenn Buzzertest ab current_event 172:
  if (current_event == 172) {
    Buzzerstate_1 = digitalRead(Buzzer_1);
    if (B1_last != Buzzerstate_1 && digitalRead(Buzzer_1) == HIGH) {
      Serial.println("Buzzer1");
      B1_last = Buzzerstate_1;
      //digitalWrite(BuzzerlightBlue_2, HIGH);
      delay(150);
    }
  }
  else if (current_event == 173) {
    Buzzerstate_2 = digitalRead(Buzzer_2);
    if (B2_last != Buzzerstate_2 && digitalRead(Buzzer_2) == HIGH) {
      Serial.println("Buzzer2");
      B2_last = Buzzerstate_2;
      delay(150);
    }
  }
  else if (current_event == 174) {
    Buzzerstate_3 = digitalRead(Buzzer_3);
    if (B3_last != Buzzerstate_3 && digitalRead(Buzzer_3) == HIGH) {
      Serial.println("Buzzer3");
      B3_last = Buzzerstate_3;
      delay(150);
    }
  }

  if (current_event != last_event) {
    last_event = current_event; // merken, dass es bearbeitet wurde

    switch (current_event) {
      case 1:
        reset_Buzzlights();
        waitpos();
        videopos();
        break;
      case 172:
        reset_Buzzlights();
        //digitalWrite(BuzzerlightRed_1, HIGH);
        //digitalWrite(BuzzerlightGreen_1, HIGH);
        digitalWrite(BuzzerlightBlue_1, HIGH);
        P1_buzzed();
        break;

      case 173:
        reset_Buzzlights();
        //digitalWrite(BuzzerlightRed_2, HIGH);
        //digitalWrite(BuzzerlightGreen_2, HIGH);
        digitalWrite(BuzzerlightBlue_2, HIGH);
        P2_buzzed();
        break;

      case 174:
        reset_Buzzlights();
        //digitalWrite(BuzzerlightRed_3, HIGH);
        //digitalWrite(BuzzerlightGreen_3, HIGH);
        digitalWrite(BuzzerlightBlue_3, HIGH);
        P3_buzzed();
        break;

      case 2://Fragen: alle ein
        //flag für Buzzerlocked zurücksetzen:
        BuzzerLocked = false;

        //digitalWrite(BuzzerlightRed_1, HIGH);
        //digitalWrite(BuzzerlightRed_2, HIGH);
        //digitalWrite(BuzzerlightRed_3, HIGH);
        //digitalWrite(BuzzerlightGreen_1, HIGH);
        //digitalWrite(BuzzerlightGreen_2, HIGH);
        //digitalWrite(BuzzerlightGreen_3, HIGH);
        digitalWrite(BuzzerlightBlue_1, HIGH);
        digitalWrite(BuzzerlightBlue_2, HIGH);
        digitalWrite(BuzzerlightBlue_3, HIGH);
        waitpos_2();
        break;
      case 31://B1 gedrückt bei event 2:
        reset_Buzzlights();
        //digitalWrite(BuzzerlightRed_1, HIGH);
        //digitalWrite(BuzzerlightGreen_1, HIGH);
        digitalWrite(BuzzerlightBlue_1, HIGH);
        P1_buzzed();
        break;

      case 32://B2 gedrückt bei event 2:
        reset_Buzzlights();
        //digitalWrite(BuzzerlightRed_2, HIGH);
        //digitalWrite(BuzzerlightGreen_2, HIGH);
        digitalWrite(BuzzerlightBlue_2, HIGH);
        P2_buzzed();
        break;

      case 33://B3 gedrückt bei event 2:
        reset_Buzzlights();
        //digitalWrite(BuzzerlightRed_3, HIGH);
        //digitalWrite(BuzzerlightGreen_3, HIGH);
        digitalWrite(BuzzerlightBlue_3, HIGH);
        P3_buzzed();
        break;

      case 41://B1 falsch
        reset_Buzzlights();
        digitalWrite(BuzzerlightRed_1, HIGH);
        P1_wrong();
        break;

      case 42://B2 falsch
        reset_Buzzlights();
        digitalWrite(BuzzerlightRed_2, HIGH);
        P2_wrong();
        break;

      case 43://B3 falsch
        reset_Buzzlights();
        digitalWrite(BuzzerlightRed_3, HIGH);
        P3_wrong();
        break;

      case 51://B1 richtig
        reset_Buzzlights();
        digitalWrite(BuzzerlightGreen_1, HIGH);
        P1_right();
        break;

      case 52://B2 richtig
        reset_Buzzlights();
        digitalWrite(BuzzerlightGreen_2, HIGH);
        P2_right();
        break;

      case 53://B3 richtig
        reset_Buzzlights();
        digitalWrite(BuzzerlightGreen_3, HIGH);
        P3_right();
        break;

      case 61:
        reset_Buzzlights();
        digitalWrite(BuzzerlightRed_1, HIGH);
        digitalWrite(BuzzerlightRed_2, HIGH);
        digitalWrite(BuzzerlightRed_3, HIGH);
        P2_wrong();
        break;

      case 62:
        reset_Buzzlights();
        digitalWrite(BuzzerlightGreen_1, HIGH);
        digitalWrite(BuzzerlightRed_2, HIGH);
        digitalWrite(BuzzerlightRed_3, HIGH);
        break;
      
      case 63:
        reset_Buzzlights();
        digitalWrite(BuzzerlightRed_1, HIGH);
        digitalWrite(BuzzerlightRed_2, HIGH);
        digitalWrite(BuzzerlightGreen_3, HIGH);
        break;

      case 64:
        reset_Buzzlights();
        digitalWrite(BuzzerlightRed_1, HIGH);
        digitalWrite(BuzzerlightGreen_2, HIGH);
        digitalWrite(BuzzerlightRed_3, HIGH);
        break;

      case 65:
        reset_Buzzlights();
        digitalWrite(BuzzerlightGreen_1, HIGH);
        digitalWrite(BuzzerlightGreen_2, HIGH);
        digitalWrite(BuzzerlightRed_3, HIGH);
        break;

      case 66:
        reset_Buzzlights();
        digitalWrite(BuzzerlightGreen_1, HIGH);
        digitalWrite(BuzzerlightRed_2, HIGH);
        digitalWrite(BuzzerlightGreen_3, HIGH);
        break;

      case 67:
        reset_Buzzlights();
        digitalWrite(BuzzerlightRed_1, HIGH);
        digitalWrite(BuzzerlightGreen_2, HIGH);
        digitalWrite(BuzzerlightGreen_3, HIGH);
        break;

      case 989:
        reset_Buzzlights();
        videopos();
        break;

      default:
        break;
    }
  }
}

//Funktionen fürs licht ----------------------------------------------------------------------------------------------------------------------------------------------
void Reset(){
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(31, 0);
  DmxSimple.write(33, 0);
  DmxSimple.write(37, 255);
  for (int i = 8; i < 15; i++) {
    DmxSimple.write(30+i, 0);
  }
  for (int f = 2; f < 15; f++) {
    DmxSimple.write(f, 0);
  }
  }
}
void P1_buzzed() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(31, 100);
  DmxSimple.write(33, 175);
  delay(250);
  DmxSimple.write(39, 0);
  DmxSimple.write(40, 0);
  DmxSimple.write(38, 0);
  DmxSimple.write(41, 255);
  //alle wash weiss
  dmx_wash(1, 255);
  dmx_wash(2, 255);
  dmx_wash(3, 255);

  delay(75);
  DmxSimple.write(41, 0);
  //alle wash weiss
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  dmx_wash(1, 0);
  
  delay(75);
  DmxSimple.write(41, 255);
  //alle wash weiss
  dmx_wash(2, 255);
  dmx_wash(3, 255);
  dmx_wash(1, 255);

  delay(75);
  DmxSimple.write(41, 0);
  //alle wash weiss
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  dmx_wash(1, 0);
  
  delay(75);
  DmxSimple.write(41, 255);
  //alle wash weiss
  dmx_wash(2, 255);
  dmx_wash(3, 255);
  dmx_wash(1, 255);
  
  delay(75);
  DmxSimple.write(41, 0);
  //alle wash weiss
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  dmx_wash(1, 0);
  
  delay(75);
  //alle wash weiss
  dmx_wash(2, 255);
  dmx_wash(3, 255);
  dmx_wash(1, 255);

  DmxSimple.write(41, 255);
  }
}
void P2_buzzed() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(31, 87);
  DmxSimple.write(33, 175);
  delay(250);
  DmxSimple.write(39, 0);
  DmxSimple.write(40, 0);
  DmxSimple.write(38, 0);
  DmxSimple.write(41, 255);
  //alle wash weiss
  dmx_wash(2, 255);
  dmx_wash(3, 255);
  dmx_wash(1, 255);

  delay(75);
  DmxSimple.write(41, 0);
  //alle wash weiss
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  dmx_wash(1, 0);
  
  delay(75);
  DmxSimple.write(41, 255);
  //alle wash weiss
  dmx_wash(2, 255);
  dmx_wash(3, 255);
  dmx_wash(1, 255);

  delay(75);
  DmxSimple.write(41, 0);
  //alle wash weiss
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  dmx_wash(1, 0);
  
  delay(75);
  DmxSimple.write(41, 255);
  //alle wash weiss
  dmx_wash(2, 255);
  dmx_wash(3, 255);
  dmx_wash(1, 255);
  
  delay(75);
  DmxSimple.write(41, 0);
  //alle wash weiss
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  dmx_wash(1, 0);
  
  delay(75);
  //alle wash weiss
  dmx_wash(2, 255);
  dmx_wash(3, 255);
  dmx_wash(1, 255);
  }
}
void P3_buzzed() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(31, 73);
  DmxSimple.write(33, 175);
  delay(250);
  DmxSimple.write(39, 0);
  DmxSimple.write(40, 0);
  DmxSimple.write(38, 0);
  DmxSimple.write(41, 255);
  //alle wash weiss
  dmx_wash(2, 255);
  dmx_wash(3, 255);
  dmx_wash(1, 255);

  delay(75);
  DmxSimple.write(41, 0);
  //alle wash weiss
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  dmx_wash(1, 0);
  
  delay(75);
  DmxSimple.write(41, 255);
  //alle wash weiss
  dmx_wash(2, 255);
  dmx_wash(3, 255);
  dmx_wash(1, 255);

  delay(75);
  DmxSimple.write(41, 0);
  //alle wash weiss
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  dmx_wash(1, 0);
  
  delay(75);
  DmxSimple.write(41, 255);
  //alle wash weiss
  dmx_wash(2, 255);
  dmx_wash(3, 255);
  dmx_wash(1, 255);
  
  delay(75);
  DmxSimple.write(41, 0);
  //alle wash weiss
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  dmx_wash(1, 0);
  
  delay(75);
  //alle wash weiss
  dmx_wash(2, 255);
  dmx_wash(3, 255);
  dmx_wash(1, 255);
  }
}
void waitpos() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(31, 87);
  DmxSimple.write(33, 120);
  delay(350);
  DmxSimple.write(39, 0);
  DmxSimple.write(40, 10);
  DmxSimple.write(38, 0);
  DmxSimple.write(41, 0);
  dmx_wash(1, 0);
  dmx_wash(2, 0);
  dmx_wash(3, 10);
  }
}
void waitpos_2() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(39, 0);
  DmxSimple.write(40, 10);
  DmxSimple.write(38, 0);
  DmxSimple.write(41, 0);
  dmx_wash(1, 0);
  dmx_wash(2, 0);
  dmx_wash(3, 10);
  }
}

void P1_wrong() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(41, 0);
  DmxSimple.write(31, 100);
  DmxSimple.write(33, 175);
  DmxSimple.write(39, 0);
  DmxSimple.write(40, 0);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  delay(75);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  delay(75);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  delay(75);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  delay(75);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  delay(75);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  delay(75);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  delay(2000);
  waitpos();
  }
}
void P2_wrong() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(41, 0);
  DmxSimple.write(31, 87);
  DmxSimple.write(33, 175);
  DmxSimple.write(39, 0);
  DmxSimple.write(40, 0);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  delay(75);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  delay(75);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  delay(75);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  delay(75);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  delay(75);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  delay(75);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  delay(2000);
  waitpos();
  }
}
void P3_wrong() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(41, 0);
  DmxSimple.write(31, 73);
  DmxSimple.write(33, 175);
  DmxSimple.write(39, 0);
  DmxSimple.write(40, 0);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  dmx_wash(2, 0);
  dmx_wash(3, 0);
  delay(75);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  delay(75);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  delay(75);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  delay(75);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  delay(75);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  delay(75);
  DmxSimple.write(38, 255);
  dmx_wash(1, 255);
  delay(2000);
  waitpos();
  }
}
void P1_right() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(41, 0);
  DmxSimple.write(31, 100);
  DmxSimple.write(33, 175);
  DmxSimple.write(39, 255);
  DmxSimple.write(40, 0);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  dmx_wash(2, 255);
  dmx_wash(3, 0);
  delay(2000);
  waitpos();
  }
}
void P2_right() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(41, 0);
  DmxSimple.write(31, 87);
  DmxSimple.write(33, 175);
  DmxSimple.write(39, 255);
  DmxSimple.write(40, 0);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  dmx_wash(2, 255);
  dmx_wash(3, 0);
  delay(2000);
  waitpos();
  }
}
void P3_right() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(41, 0);
  DmxSimple.write(31, 73);
  DmxSimple.write(33, 175);
  DmxSimple.write(39, 255);
  DmxSimple.write(40, 0);
  DmxSimple.write(38, 0);
  dmx_wash(1, 0);
  dmx_wash(2, 255);
  dmx_wash(3, 0);
  delay(2000);
  waitpos();
  }
}
void videopos() {
  if (Lock_QUIZDMX == false) {
  DmxSimple.write(31, 87);
  DmxSimple.write(33, 120);
  delay(350);
  DmxSimple.write(39, 0);
  DmxSimple.write(40, 10);
  DmxSimple.write(38, 0);
  DmxSimple.write(41, 0);
  dmx_wash(1, 0);
  dmx_wash(2, 0);
  dmx_wash(3, 10);

  //fade-out Blau wash:
  for (int i = 10; i>0; i--) {
    DmxSimple.write(40, i);
    delay(50);
  }
  for (int i = 10; i>0; i--) {
    dmx_wash(3, i);
    delay(50);
  }
  }
}
void reset_Buzzlights() {
  digitalWrite(BuzzerlightRed_1, LOW);
  digitalWrite(BuzzerlightRed_2, LOW);
  digitalWrite(BuzzerlightRed_3, LOW);
  digitalWrite(BuzzerlightGreen_1, LOW);
  digitalWrite(BuzzerlightGreen_2, LOW);
  digitalWrite(BuzzerlightGreen_3, LOW);
  digitalWrite(BuzzerlightBlue_1, LOW);
  digitalWrite(BuzzerlightBlue_2, LOW);
  digitalWrite(BuzzerlightBlue_3, LOW);

}
void change_channels() {
  if (change_channel == 0)  {
    change_channel = 1;
  }
  else if (change_channel == 1) {
    change_channel = 2;
  }
  else if (change_channel == 2) {
    change_channel = 0;
  }
  if (change_channel == 1) {
    channelAdd = 1;
  }
  else if (change_channel == 0) {
    channelAdd = 0;
    DmxSimple.write(4, 0);
  }
  else if (change_channel == 2) {
    channelAdd = 0;
    DmxSimple.write(4, 255);
  }
  //Serial.println("dmxch" + channelAdd);
}
void dmx_wash(int ch, int v) {
  int value = 0;
  if (channelAdd == 1) {
    DmxSimple.write(1, 255);
  }
  value = channelAdd + ch;
  //DmxSimple.write(4, 255);
  DmxSimple.write(value, v);
}
void applyScene(String data){

  data.remove(0,2);


  while(data.length()>0){


    int sep=data.indexOf(';');

    String part;


    if(sep==-1){

      part=data;
      data="";

    }
    else{

      part=data.substring(0,sep);

      data.remove(0,sep+1);

    }


    int colon=part.indexOf(':');


    if(colon>0){

      int ch =
        part.substring(0,colon).toInt();


      int val =
        part.substring(colon+1).toInt();


      DmxSimple.write(
        ch,
        val
      );

    }

  }


  Lock_QUIZDMX=true;

}
void clearDMX(){

  for(int i=1;i<=512;i++){

    DmxSimple.write(
      i,
      0
    );

  }

  Lock_QUIZDMX=true;

}