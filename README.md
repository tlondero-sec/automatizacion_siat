# 🤖 Automatización de Consulta y Descarga de Tasas Municipalidad de Paraná (SIAT)

Este proyecto automatiza la verificación de estados de deuda y la descarga de boletas digitales (PDF) desde el portal **SIAT (Sistema Integral de Administración Tributaria)** de la Municipalidad de Paraná, Entre Ríos.

Soporta la consulta automatizada de múltiples inmuebles registrados en un archivo `JSON`, procesando de forma dinámica tanto la **Tasa General Inmobiliaria (TGI - ID 14)** como la **Tasa por Servicios Sanitarios (TSS - ID 58)**.

---

## 🚀 Características

- **Consulta Multipropiedad**: Lee las partidas catastrales y códigos de gestión directamente desde `propiedades.json`.
- **Soporte Multitasa**: Verifica automáticamente **TGI** y **TSS** por cada propiedad en una sola ejecución.
- **Detección y Alerta de Deuda**: Compara el importe total en el sistema contra el período actual para detectar saldos pendientes o deuda acumulada.
- **Descarga y Renombrado Automático**: Procesa el flujo completo de reconfección en el portal SIAT (`AdministrarLiqReconfeccion.do`), descarga la boleta en PDF y la renombra con la nomenclatura: `[ID_PROPIEDAD]_[TASA]_[PERIODO].pdf`.
- **Evolución y Evidencia**: Toma capturas de pantalla (`capturas/`) de la consulta de cada inmueble.
- **Manejo de Importes Cero**: Omite descargas innecesarias cuando el período no registra saldo a pagar (`$0.00`).

---

## 🛠️ Requisitos Previos

- **Python 3.10+**
- **Google Chrome** instalado en el sistema.
- **Selenium WebDriver** (Google Chrome Service).

---

## 📦 Instalación

1. Clonar el repositorio:
   ```bash
   git clone [https://github.com/tu-usuario/automatizacion_siat.git](https://github.com/tu-usuario/automatizacion_siat.git)
   cd automatizacion_siat