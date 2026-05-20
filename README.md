<div align="center">

# Sistema de Venta de Pasajes Terrestres Interprovinciales

Proyecto académico desarrollado para el curso **Taller de Lenguaje de Programación**.

Sistema web para la gestión de venta de pasajes, rutas, promociones, clientes, encomiendas y administración interna de una empresa de transporte terrestre.

</div>

---

## Descripción

Este sistema permite administrar los procesos principales de una empresa de transporte interprovincial. Incluye interfaces públicas para clientes y módulos internos para trabajadores, facilitando la venta de pasajes, consulta de promociones, gestión de encomiendas, rutas, viajes y operaciones administrativas.

El proyecto está desarrollado con **Django** y organizado por aplicaciones para permitir un trabajo colaborativo ordenado entre los integrantes del equipo.

---

## Funcionalidades principales

- Página principal informativa.
- Registro e inicio de sesión de clientes.
- Visualización de promociones.
- Consulta de rutas y destinos.
- Interfaz de rastreo.
- Libro de reclamaciones.
- Venta de pasajes.
- Gestión de viajes, rutas y flota.
- Gestión de encomiendas.
- Panel administrativo para trabajadores.
- Control de usuarios, roles y permisos.

---

## Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| Python | Lenguaje principal |
| Django | Framework web |
| Django REST Framework | Desarrollo de funcionalidades API |
| HTML | Estructura de interfaces |
| CSS / Tailwind | Estilos visuales |
| JavaScript | Interactividad |
| PostgreSQL | Base de datos principal |
| Docker | Contenedores para la aplicación y base de datos |
| Git y GitHub | Control de versiones y trabajo colaborativo |

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
│   └── settings/
├── core/
├── static/
│   └── img/
├── templates/
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── requirements.txt
└── README.md
