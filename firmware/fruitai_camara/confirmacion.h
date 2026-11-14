// FruitAI — lógica de confirmación anti-duplicados (plan v4, día 9).
//
// Traducción línea por línea de simulador/confirmacion.py. No depende de
// Arduino: se compila igual en el ESP32 y en el PC para las pruebas
// (firmware/fruitai_camara/test/test_confirmacion.cpp).
//
// Reglas:
//  1. Una fruta queda CONFIRMADA cuando el modelo la predice framesConfirmar
//     fotogramas seguidos con confianza >= umbral (y hay presencia).
//  2. Solo con una fruta confirmada, un botón (entrada/salida) genera UN movimiento.
//  3. Después del movimiento la fruta queda REGISTRADA: más pulsaciones se ignoran
//     hasta que se retire (framesRetiro fotogramas de "fondo" o sin presencia).
//
// Estados: ESPERANDO → CONFIRMADA → (botón) → REGISTRADA → (retiro) → ESPERANDO
#pragma once

#include <math.h>
#include <stdio.h>
#include <string.h>

enum Estado { ESPERANDO, CONFIRMADA, REGISTRADA };

inline const char* nombreEstado(Estado e) {
  switch (e) {
    case CONFIRMADA: return "CONFIRMADA";
    case REGISTRADA: return "REGISTRADA";
    default:         return "ESPERANDO";
  }
}

struct Movimiento {
  bool valido;          // false = la pulsación se ignoró
  char fruta[24];
  const char* tipo;     // "entrada" | "salida"
  float confianza;
};

// Clases del modelo que se registran como la misma fruta del inventario.
struct Alias { const char* clase; const char* fruta; };
static const Alias MAPA_POR_DEFECTO[] = {
  {"manzana_roja", "manzana"},
  {"manzana_verde", "manzana"},
};

class Confirmador {
 public:
  float umbral;
  int framesConfirmar;
  int framesRetiro;

  Estado estado = ESPERANDO;
  char fruta[24] = "";      // fruta confirmada / registrada ("" = ninguna)
  float confianza = 0.0f;   // media de los fotogramas que la confirmaron
  char mensaje[96] = "";    // última explicación (para el puerto serie)

  explicit Confirmador(float umbral_ = 0.75f, int framesConfirmar_ = 5, int framesRetiro_ = 5,
                       const char* fondo = "fondo")
      : umbral(umbral_), framesConfirmar(framesConfirmar_), framesRetiro(framesRetiro_) {
    copiar(fondo_, fondo);
  }

  // Recibe la predicción de un fotograma. Devuelve el estado resultante.
  Estado procesar(const char* etiqueta, float conf, bool presencia = true) {
    const bool esFondo = strcmp(etiqueta, fondo_) == 0;
    const bool hayFruta = presencia && !esFondo && conf >= umbral;
    const char* f = hayFruta ? aFruta(etiqueta) : nullptr;

    // ¿Se retiró la fruta confirmada/registrada?
    if (estado == CONFIRMADA || estado == REGISTRADA) {
      const bool ausente = !presencia || esFondo;
      ausente_ = ausente ? ausente_ + 1 : 0;
      if (ausente_ >= framesRetiro) {
        snprintf(mensaje, sizeof(mensaje), "%s retirada", fruta);
        estado = ESPERANDO;
        fruta[0] = '\0';
        confianza = 0.0f;
        ausente_ = 0;
        reiniciarCandidata();
        return estado;
      }
      if (estado == REGISTRADA || f == nullptr || strcmp(f, fruta) == 0) return estado;
      // CONFIRMADA y ahora se ve otra fruta con buena confianza: se cuenta como
      // candidata nueva (cambio de fruta sin pasar por fondo).
    }

    if (f == nullptr) {
      reiniciarCandidata();
      return estado;
    }

    if (candidata_[0] != '\0' && strcmp(f, candidata_) == 0) {
      seguidos_++;
      sumaConf_ += conf;
    } else {
      copiar(candidata_, f);
      seguidos_ = 1;
      sumaConf_ = conf;
    }

    if (seguidos_ >= framesConfirmar) {
      estado = CONFIRMADA;
      copiar(fruta, f);
      confianza = roundf(sumaConf_ / seguidos_ * 100.0f) / 100.0f;
      ausente_ = 0;
      reiniciarCandidata();
      snprintf(mensaje, sizeof(mensaje), "%s confirmada (%d%%). Pulsa entrada o salida", fruta,
               (int)lroundf(confianza * 100));
    }
    return estado;
  }

  // Pulsación de un botón ("entrada" | "salida"). Devuelve el movimiento a
  // publicar; si valido == false, la pulsación se ignoró (ver mensaje).
  Movimiento boton(const char* tipo) {
    Movimiento m{};
    m.valido = false;
    m.tipo = strcmp(tipo, "salida") == 0 ? "salida" : "entrada";
    if (estado == ESPERANDO) {
      snprintf(mensaje, sizeof(mensaje), "Ignorado: no hay una fruta confirmada");
      return m;
    }
    if (estado == REGISTRADA) {
      snprintf(mensaje, sizeof(mensaje), "Ignorado: %s ya se registro; retirala antes de otro registro",
               fruta);
      return m;
    }
    m.valido = true;
    copiar(m.fruta, fruta);
    m.confianza = confianza;
    estado = REGISTRADA;
    snprintf(mensaje, sizeof(mensaje), "Registrado: %s de %s", m.tipo, fruta);
    return m;
  }

 private:
  char fondo_[24];
  char candidata_[24] = "";
  int seguidos_ = 0;
  float sumaConf_ = 0.0f;
  int ausente_ = 0;

  static void copiar(char* destino, const char* origen) {
    strncpy(destino, origen, 23);
    destino[23] = '\0';
  }

  static const char* aFruta(const char* etiqueta) {
    for (const Alias& a : MAPA_POR_DEFECTO)
      if (strcmp(etiqueta, a.clase) == 0) return a.fruta;
    return etiqueta;
  }

  void reiniciarCandidata() {
    candidata_[0] = '\0';
    seguidos_ = 0;
    sumaConf_ = 0.0f;
  }
};
