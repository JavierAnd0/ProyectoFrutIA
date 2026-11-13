// Pruebas de confirmacion.h en el PC (sin ESP32). Son las mismas de
// simulador/tests/test_confirmacion.py, para comprobar que el C++ del firmware
// se comporta igual que la versión Python del ESP32 virtual.
//
//   g++ -std=c++17 -Wall -Wextra -I.. test_confirmacion.cpp -o /tmp/t && /tmp/t
//   (o: ./scripts/probar_firmware.sh)
#include <cstdio>
#include <cstring>
#include <initializer_list>

#include "confirmacion.h"

static int fallos = 0, total = 0;
#define CHECK(c)                                                    \
  do {                                                              \
    total++;                                                        \
    if (!(c)) {                                                     \
      fallos++;                                                     \
      printf("  FALLA %s:%d  %s\n", __func__, __LINE__, #c);        \
    }                                                               \
  } while (0)

static Estado ver(Confirmador& c, const char* et, int veces, float conf = 0.9f, bool pres = true) {
  Estado e = c.estado;
  for (int i = 0; i < veces; i++) e = c.procesar(et, conf, pres);
  return e;
}
static bool eq(const char* a, const char* b) { return strcmp(a, b) == 0; }

static void confirma_tras_n_fotogramas_seguidos() {
  Confirmador c(0.75f, 5);
  CHECK(ver(c, "pera", 4) == ESPERANDO);
  CHECK(ver(c, "pera", 1) == CONFIRMADA);
  CHECK(eq(c.fruta, "pera") && c.confianza == 0.9f);
}

static void baja_confianza_o_fondo_reinicia_la_cuenta() {
  Confirmador c(0.75f, 3);
  ver(c, "kiwi", 2);
  c.procesar("kiwi", 0.5f);
  CHECK(ver(c, "kiwi", 2) == ESPERANDO);
  c.procesar("fondo", 0.99f);
  CHECK(ver(c, "kiwi", 2) == ESPERANDO);
  CHECK(ver(c, "kiwi", 1) == CONFIRMADA);
}

static void predicciones_alternadas_no_confirman() {
  Confirmador c(0.75f, 3);
  for (int i = 0; i < 10; i++) {
    c.procesar("pera", 0.9f);
    c.procesar("kiwi", 0.9f);
  }
  CHECK(c.estado == ESPERANDO);
}

static void sin_presencia_no_confirma() {
  Confirmador c(0.75f, 3);
  CHECK(ver(c, "banano", 10, 0.9f, false) == ESPERANDO);
}

static void boton_sin_fruta_se_ignora() {
  Confirmador c;
  CHECK(!c.boton("entrada").valido);
  CHECK(strstr(c.mensaje, "no hay una fruta") != nullptr);
}

static void un_solo_movimiento_aunque_se_pulse_varias_veces() {
  Confirmador c(0.75f, 3);
  ver(c, "banano", 3);
  Movimiento m = c.boton("salida");
  CHECK(m.valido && eq(m.fruta, "banano") && eq(m.tipo, "salida"));
  CHECK(c.estado == REGISTRADA);
  ver(c, "banano", 20);
  CHECK(!c.boton("salida").valido);
  CHECK(!c.boton("entrada").valido);
}

static void retirar_la_fruta_rearma_para_el_siguiente_registro() {
  Confirmador c(0.75f, 3, 4);
  ver(c, "pera", 3);
  CHECK(c.boton("entrada").valido);
  ver(c, "fondo", 3);
  CHECK(c.estado == REGISTRADA);
  ver(c, "fondo", 1);
  CHECK(c.estado == ESPERANDO);
  ver(c, "pera", 3);
  CHECK(c.boton("entrada").valido);
}

static void un_parpadeo_de_fondo_no_cuenta_como_retiro() {
  Confirmador c(0.75f, 3, 4);
  ver(c, "pera", 3);
  c.boton("entrada");
  ver(c, "fondo", 2);
  ver(c, "pera", 1);
  ver(c, "fondo", 3);
  CHECK(c.estado == REGISTRADA);
}

static void quitar_presencia_cuenta_como_retiro() {
  Confirmador c(0.75f, 3, 4);
  ver(c, "kiwi", 3);
  c.boton("entrada");
  CHECK(ver(c, "kiwi", 4, 0.9f, false) == ESPERANDO);
}

static void clases_de_manzana_se_registran_como_manzana() {
  Confirmador c(0.75f, 4);
  const char* seq[] = {"manzana_roja", "manzana_verde", "manzana_roja", "manzana_verde"};
  for (const char* e : seq) c.procesar(e, 0.9f);
  CHECK(c.estado == CONFIRMADA && eq(c.fruta, "manzana"));
  CHECK(eq(c.boton("entrada").fruta, "manzana"));
}

static void cambiar_de_fruta_sin_pasar_por_fondo() {
  Confirmador c(0.75f, 3);
  ver(c, "pera", 3);
  ver(c, "kiwi", 3);
  CHECK(c.estado == CONFIRMADA && eq(c.fruta, "kiwi"));
}

static void confianza_es_la_media_de_los_fotogramas_que_confirmaron() {
  Confirmador c(0.75f, 3);
  for (float conf : {0.8f, 0.9f, 1.0f}) c.procesar("kiwi", conf);
  CHECK(c.confianza == 0.9f);
}

int main() {
  confirma_tras_n_fotogramas_seguidos();
  baja_confianza_o_fondo_reinicia_la_cuenta();
  predicciones_alternadas_no_confirman();
  sin_presencia_no_confirma();
  boton_sin_fruta_se_ignora();
  un_solo_movimiento_aunque_se_pulse_varias_veces();
  retirar_la_fruta_rearma_para_el_siguiente_registro();
  un_parpadeo_de_fondo_no_cuenta_como_retiro();
  quitar_presencia_cuenta_como_retiro();
  clases_de_manzana_se_registran_como_manzana();
  cambiar_de_fruta_sin_pasar_por_fondo();
  confianza_es_la_media_de_los_fotogramas_que_confirmaron();
  printf("%d/%d comprobaciones OK\n", total - fallos, total);
  return fallos ? 1 : 0;
}
