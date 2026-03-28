# 🦊 GitLab Architect CLI

**GitLab Architect CLI** es una herramienta de terminal avanzada diseñada para la gestión granular y escalable de infraestructuras en GitLab. Desarrollada con un enfoque en **eficiencia algorítmica** y **resiliencia de sistemas**, permite visualizar jerarquías complejas y automatizar operaciones de gestión de grupos y variables que el CLI estándar no cubre con la misma elegancia.

> "La simplicidad es la máxima sofisticación." — Inspirado en los principios de diseño de sistemas de **Leonardo da Vinci** y la rigurosidad matemática de **Euler**.

---

## 🚀 Características Principales

* **Visualización de Jerarquía Estructural (Live Tree):** Generación de árboles en tiempo real utilizando algoritmos de recursión controlada para mapear grupos, subgrupos y proyectos.
* **Gestión de Variables de Entorno:** CRUD completo de secretos a nivel de grupo con soporte para scopes y protección de datos.
* **Orquestación de Subgrupos:** Creación, eliminación y transferencia (move) de subgrupos respetando la integridad de la ruta.
* **Raw API Access:** Interfaz directa con la API REST de GitLab para ejecutar cualquier endpoint documentado, devolviendo JSON formateado.
* **Resiliencia SRE:** Manejo avanzado de errores (500 Internal Server Errors, Timeouts) y paginación optimizada para evitar la saturación de buffers de red.

---

## 🛠 Arquitectura Técnica

El script está diseñado siguiendo patrones de **Inyección de Dependencias** y **Single Responsibility Principle (SRP)**.

### Complejidad Algorítmica

La visualización del árbol opera con una complejidad de tiempo de , donde:

*  es el número de subgrupos.
*  es el número de proyectos.

Se ha implementado un límite de profundidad para evitar el desbordamiento de pila y latencia excesiva en infraestructuras de nivel Enterprise.

---

## 📦 Instalación y Configuración

### Requisitos Previos

* Python 3.12+
* GitLab Private Token con permisos de `api`.

### Setup

1. **Clonar el repositorio:**
```bash
git clone https://github.com/NaEspinoza/GlabManager.git
cd GlabManager

```


2. **Instalar dependencias:**
```bash
pip install -r requirements.txt

```


3. **Configurar variables de entorno:**
```bash
Ver archivo .env y configurar

```
	O en la terminal:
```bash
export GITLAB_PRIVATE_TOKEN='tu_token_aqui'
export GITLAB_URL='https://gitlab.com' # O tu instancia self-hosted

```



---

## 🖥 Uso

Ejecuta el orquestador principal:

```bash
python main.py

```

### Funciones Destacadas del Menú:

1. **Live Tree:** Introduce un ID de grupo y observa cómo se construye el grafo de dependencias en vivo.
2. **Transferencia de Grupos:** Mueve subgrupos entre diferentes padres de forma atómica.
3. **Raw Request:** Ejecuta `GET /projects/:id/issues` o cualquier endpoint de la [OpenAPI de GitLab](https://docs.gitlab.com/api/openapi/openapi_interactive/).

---

## 🛡 Seguridad (SRE Best Practices)

* **No Hardcoded Secrets:** El script prohíbe el uso de tokens en el código fuente, exigiendo variables de entorno.
* **Timeout Control:** Implementación de timeouts en las peticiones para evitar procesos zombis en entornos de CI/CD.
* **Masking:** Las variables de entorno se listan con máscaras para prevenir filtraciones visuales en demostraciones o logs.

---
## 👤 Creador
**Nazareno Espinoza**
---

## 📜 Licencia

Este proyecto está bajo la [Licencia Apache-2.0](LICENSE). Siéntete libre de usarlo y mejorarlo , siempre y cuando se aclare el uso de los derechos de copyright.
