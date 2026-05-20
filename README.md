<div align="center">

# Sistema de Venta de Pasajes Terrestres Interprovinciales

Proyecto web desarrollado para el curso **Taller de Lenguaje de Programación**.

Sistema orientado a la gestión de venta de pasajes, rutas, promociones, clientes, encomiendas y administración interna para una empresa de transporte terrestre.

</div>

---

## Descripción

Este proyecto permite simular y administrar el flujo principal de una empresa de transporte interprovincial, incluyendo interfaces públicas para clientes y módulos internos para la gestión operativa.

El sistema está desarrollado con una arquitectura web basada en Django, separando las funcionalidades por módulos para facilitar el trabajo colaborativo del equipo.

---

## Funcionalidades principales

- Página principal informativa.
- Visualización de promociones.
- Registro e inicio de sesión de clientes.
- Consulta de rutas y destinos.
- Interfaz de rastreo.
- Libro de reclamaciones.
- Gestión de ventas de pasajes.
- Administración de viajes, rutas y flota.
- Gestión de encomiendas.
- Panel administrativo para trabajadores.

---

## Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| Python | Lenguaje principal |
| Django | Framework web |
| HTML | Estructura de interfaces |
| CSS / Tailwind | Estilos visuales |
| JavaScript | Interactividad |
| SQLite / Base de datos | Persistencia de datos |
| Git y GitHub | Control de versiones |

---

## Estructura del proyecto

```txt
Taller-de-Lenguaje-de-Programacion/
│
├── apps/
│   ├── cuentas/
│   ├── encomiendas/
│   ├── flota/
│   ├── panel/
│   ├── promociones/
│   ├── publico/
│   ├── rutas/
│   ├── ventas/
│   └── viajes/
│
├── config/
├── core/
├── static/
│   └── img/
├── templates/
├── manage.py
└── requirements.txt
