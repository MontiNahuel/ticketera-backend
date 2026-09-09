# 🎫 Sistema de Tickets - Backend (FastAPI + MongoDB GridFS)

Backend robusto para la gestión y seguimiento de tickets de soporte con almacenamiento nativo de imágenes en **MongoDB GridFS**, arquitectura en capas y soporte de **Rollback automático**.

> Copia mantenida para despliegue en Railway.

---

## 🛠️ Tecnologías Utilizadas

- **Lenguaje**: Python 3.12+
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asíncrono, OpenAPI 3.1)
- **ODM / Base de Datos**: [Beanie](https://beanie-odm.dev/) & [Motor](https://motor.readthedocs.io/) (MongoDB Async)
- **Almacenamiento de Archivos**: **MongoDB GridFS** nativo en streams
- **Validación de Datos**: [Pydantic v2](https://docs.pydantic.dev/)
- **Servidor ASGI**: [Uvicorn](https://www.uvicorn.org/)
- **Testing**: [Pytest](https://docs.pytest.org/)

---

## 🚀 Guía de Inicio Rápido (Setup)

### 1. Clonar el repositorio
```bash
git clone <URL_DEL_REPOSITORIO>
cd ticketscoopya_backend
```

### 2. Crear y activar el entorno virtual

- **En Windows**:
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```
- **En Linux / macOS**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crea el archivo `.env` a partir de `.env.example`:
- **En Windows**:
  ```bash
  copy .env.example .env
  ```
- **En Linux / macOS**:
  ```bash
  cp .env.example .env
  ```

Asegúrate de que MongoDB esté corriendo en tu sistema o ajusta las variables dentro del archivo `.env`:
```env
MONGO_URI=mongodb://localhost:27017/tickets_db
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]
ADMIN_EMAILS=["admin@coopya.com", "nahuel@coopya.com"]  # Admins exentos de cooldown y rate limit
```

### 5. Iniciar el servidor
```bash
uvicorn src.main:app --reload
```

---

## 🌐 URLs de Acceso

- 📖 **Documentación Interactiva (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 📑 **Documentación Alternativa (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- 🎫 **Visor Web de Tickets (Frontend Integrado)**: [http://localhost:8000/](http://localhost:8000/)
- 🩺 **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📌 Guía de Endpoints y Payloads para Frontend

Base URL: `http://localhost:8000/api/v1`

---

### 1. 🎫 Tickets (`/api/v1/tickets`)

#### `POST /api/v1/tickets/` — Crear Ticket con Imágenes
> **Content-Type**: `multipart/form-data`  
> **Seguridad**: Cooldown de 60 segundos por correo y máximo 8 tickets diarios (excepto si el correo está configurado en `ADMIN_EMAILS`).  
> **Formatos de imagen permitidos**: PNG, JPEG, JPG, WebP, GIF, SVG, AVIF, BMP.

**Campos del Formulario (`FormData`)**:
| Campo | Tipo | Obligatorio | Descripción | Ejemplo |
| :--- | :--- | :---: | :--- | :--- |
| `titulo` | `string` | Sí | Título del problema (3-150 caracteres) | `"Falla en impresora de recepción"` |
| `descripcion` | `string` | Sí | Detalle completo del incidente | `"No toma papel y parpadea luz roja"` |
| `correo` | `string (email)` | Sí | Correo del solicitante | `"carlos@coopya.com"` |
| `prioridad` | `string` | No | `"baja" \| "media" \| "alta" \| "critica"` (default: `"media"`) | `"alta"` |
| `asignar` | `string` | No | Nombre del técnico asignado | `"Facundo Bernard"` |
| `columna` | `int` | No | Columna del tablero: `1` (TICKET), `2` (HITOS), `3` (TAREAS), `4` (TAREAS PERIÓDICAS). (default: `1`) | `1` |
| `frecuencia` | `string (JSON)` | No | Objeto serializado JSON con frecuencia para tareas periódicas | `{"numero": 1, "periodo": "Semanas"}` |
| `files` | `File[] (binario)` | No | Archivos de imagen adjuntos (múltiples) | `captura1.png`, `foto2.jpg` |

> ℹ️ **Valores permitidos para `periodo` en `frecuencia`**: `"Días"`, `"Semanas"`, `"Meses"`, `"Años"` (con mayúscula inicial y tildes exactas). `numero` debe ser un entero `>= 1`.

**Respuesta Exitosa (`201 Created`)**:
```json
{
  "id": "66d34b9e4a1b2c3d4e5f6a7b",
  "identificador": "TCK-1001",
  "titulo": "Falla en impresora de recepción",
  "descripcion": "No toma papel y parpadea luz roja",
  "correo": "carlos@coopya.com",
  "prioridad": "alta",
  "estado": "abierto",
  "asignar": "Facundo Bernard",
  "columna": 1,
  "leido": false,
  "frecuencia": null,
  "imagenes": [
    "/api/v1/files/66d34b9e4a1b2c3d4e5f6a7c",
    "/api/v1/files/66d34b9e4a1b2c3d4e5f6a7d"
  ],
  "fecha_creacion": "2026-08-31T18:24:39.123456Z",
  "fecha_edicion": null
}
```

---

#### `GET /api/v1/tickets/` — Listar Tickets (con Filtros y Paginación)
> **Método**: `GET`  
> **Query Params (todos opcionales)**:

| Parámetro | Tipo | Descripción | Ejemplo |
| :--- | :--- | :--- | :--- |
| `columna` | `int` | Filtro por columna (`1, 2, 3, 4`) | `1` |
| `leido` | `bool` | Filtro por estado de lectura (`true` o `false`) | `false` |
| `fecha_desde` | `string` | Filtro desde fecha (autocompleta a las 00:00 UTC) | `2026-08-01` o `01/08/2026` |
| `fecha_hasta` | `string` | Filtro hasta fecha (autocompleta a las 23:59 UTC) | `2026-08-31` o `31/08/2026` |
| `estado` | `string` | `"abierto" \| "en_progreso" \| "resuelto" \| "cerrado"` | `en_progreso` |
| `prioridad` | `string` | `"baja" \| "media" \| "alta" \| "critica"` | `critica` |
| `asignar` | `string` | Búsqueda parcial / insensible a mayúsculas | `Facundo` |
| `skip` | `int` | Paginación: registros a omitir (default: `0`) | `0` |
| `limit` | `int` | Paginación: cantidad a traer (default: `100`, máx: `500`) | `20` |

**Respuesta Exitosa (`200 OK`)**:
```json
[
  {
    "id": "66d34b9e4a1b2c3d4e5f6a7b",
    "identificador": "TCK-1001",
    "titulo": "Falla en impresora",
    "descripcion": "No toma papel",
    "correo": "carlos@coopya.com",
    "prioridad": "alta",
    "estado": "abierto",
    "asignar": "Facundo Bernard",
    "columna": 1,
    "leido": false,
    "frecuencia": null,
    "imagenes": ["/api/v1/files/66d34b9e4a1b2c3d4e5f6a7c"],
    "fecha_creacion": "2026-08-31T18:24:39.123456Z",
    "fecha_edicion": null
  }
]
```

---

#### `GET /api/v1/tickets/{id}` — Detalle de Ticket
- **Respuesta (`200 OK`)**: Objeto `TicketResponse`.
- **Respuesta (`404 Not Found`)**: `{"error": "Not Found", "message": "Ticket con id ... no encontrado"}`

---

#### `PATCH /api/v1/tickets/{id}` — Actualizar Estado o Campos
> **Content-Type**: `application/json`  
> Permite enviar únicamente los campos que se desean modificar.

**Payload de Entrada**:
```json
{
  "estado": "en_progreso",
  "asignar": "Nahuel Monti",
  "prioridad": "critica",
  "columna": 2,
  "frecuencia": {
    "numero": 2,
    "periodo": "Meses"
  }
}
```

**Respuesta (`200 OK`)**: Objeto `TicketResponse` con `fecha_edicion` actualizada automáticamente en UTC.

---

#### `PATCH /api/v1/tickets/{id}/read` — Marcar Ticket como Leído
> **Método**: `PATCH`  
> Actualiza el flag `leido = true` cuando un operador abre o visualiza el ticket en el frontend.

**Respuesta (`200 OK`)**: Objeto `TicketResponse` con `leido: true`.

---

#### `GET /api/v1/tickets/stream` — Canal en Tiempo Real (Server-Sent Events - SSE)
> **Método**: `GET`  
> **Content-Type**: `text/event-stream`  
> Conexión persistente unidireccional (ligera, nativa de HTTP/FastAPI) que emite un evento cada vez que entra un nuevo ticket a la base de datos.
> Envía periódicamente `: ping\n\n` como keep-alive para evitar que proxies o Railway cierren la conexión por inactividad.

**Ejemplo de Integración en Frontend (React / JavaScript Nativo) con Notificaciones de Escritorio**:
```javascript
// 1. Solicitar permiso para notificaciones de escritorio al cargar
if ("Notification" in window && Notification.permission === "default") {
  Notification.requestPermission();
}

// 2. Conectar al canal SSE
const eventSource = new EventSource("http://localhost:8000/api/v1/tickets/stream");

eventSource.onmessage = (event) => {
  const newTicket = JSON.parse(event.data);
  console.log("Nuevo ticket recibido en tiempo real:", newTicket);

  // Actualizar estado / tablero en React (ej: prepend a la lista)
  // setTickets(prev => [newTicket, ...prev]);

  // Mostrar notificación nativa de escritorio
  if ("Notification" in window && Notification.permission === "granted") {
    new Notification(`🎫 Nuevo Ticket: ${newTicket.identificador}`, {
      body: `${newTicket.titulo} - Solicitante: ${newTicket.correo}`,
      icon: "/logo.png"
    });
  }
};

eventSource.onerror = (err) => {
  console.error("Error en conexión SSE, el navegador reconectará automáticamente:", err);
};

// Cerrar conexión al desmontar componente:
// eventSource.close();
```

---

#### `DELETE /api/v1/tickets/{id}` — Eliminar Ticket y sus Fotos
- **Respuesta (`204 No Content`)**: Elimina el ticket de MongoDB y borra automáticamente todas sus fotos asociadas de GridFS.

---

#### `DELETE /api/v1/tickets/{id}/images/{file_id}` — Eliminar Foto Específica
- **Respuesta (`200 OK`)**: Elimina la foto puntual de GridFS y del array `imagenes` del ticket.

---

### 2. 🧱 Catálogos (`/api/v1/catalogs`)

Todos los catálogos devuelven el formato estándar `OptionItem[]` (`[{ value, label }]`) para vincular directamente con componentes `<select>` de React.

#### `GET /api/v1/catalogs/estados`
```json
[
  { "value": "abierto", "label": "Abierto" },
  { "value": "en_progreso", "label": "En Progreso" },
  { "value": "resuelto", "label": "Resuelto" },
  { "value": "cerrado", "label": "Cerrado" }
]
```

#### `GET /api/v1/catalogs/prioridades`
```json
[
  { "value": "baja", "label": "Baja" },
  { "value": "media", "label": "Media" },
  { "value": "alta", "label": "Alta" },
  { "value": "critica", "label": "Crítica" }
]
```

#### `GET /api/v1/catalogs/asignables`
```json
[
  { "value": "facundo_bernard", "label": "Facundo Bernard" },
  { "value": "nicolas_gonzalez", "label": "Nicolas Gonzalez" },
  { "value": "nahuel_monti", "label": "Nahuel Monti" }
]
```

---

### 3. 🖼️ Archivos e Imágenes (`/api/v1/files`)

#### `GET /api/v1/files/{file_id}`
- **Respuesta**: Stream binario directo de la imagen (`image/png`, `image/jpeg`, etc.).
- **Caché**: Incluye cabecera `Cache-Control: public, max-age=86400, immutable` (caché local de 24 horas en el navegador).
- **Uso en Frontend**:
  ```tsx
  <img src={`http://localhost:8000${url}`} alt="Adjunto" loading="lazy" />
  ```

---

## 🧪 Ejecución de Pruebas Automatizadas

Para correr toda la suite de pruebas unitarias y de integración:
```bash
pytest -v
```
