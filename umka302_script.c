#include tracker
#include <time>
#include serial

#pragma dynamic 256

main() {
  for (;;) {
    new buff[120];
    new size;
    new value = 0;
    if (rsopen() == true) {
      size = rsrecv(buff, _);
      for (new i = 0; i < size; i++) {
        value = (value << 8) | (buff[i] & 0xFF);
      } 
      if ((value <= 3000) && (value >= 0)) {
        printf("Data: ");
        printf("%d\0", value);
      }
      delay(1000);
      rsclose();
    }
    delay(1000);
  }
}