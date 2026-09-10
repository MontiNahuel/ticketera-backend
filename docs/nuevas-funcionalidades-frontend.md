# 📘 Guía de Integración para Frontend: Nuevas Funcionalidades del Backend

Este documento detalla las 3 nuevas funcionalidades implementadas en el backend (`ticketera-backend`) para que el agente o desarrollador de frontend las integre en la interfaz de usuario.

---

## 📑 Índice de Contenidos
1. [Tipos TypeScript Actualizados](#1-tipos-typescript-actualizados)
2. [Cartel de "NUEVO" y Estado de Lectura (`leido`)](#2-cartel-de-nuevo-y-estado-de-lectura-leido)
3. [Notificaciones de Escritorio y Tiempo Real (SSE)](#3-notificaciones-de-escritorio-y-tiempo-real-sse)
4. [Soporte de Frecuencias Periódicas (`frecuencia`)](#4-soporte-de-frecuencias-periódicas-frecuencia)
5. [Resumen Rápido de Endpoints](#5-resumen-rápido-de-endpoints)

---

## 1. Tipos TypeScript Actualizados

Actualiza las interfaces del modelo de Ticket en tu frontend (ej. `src/types/ticket.ts` o donde residan):

```typescript
export type PeriodoFrecuencia = "Días" | "Semanas" | "Meses" | "Años";

export interface Frecuencia {
  numero: number; // Entero >= 1
  periodo: PeriodoFrecuencia;
}

export type ColumnaTicket = 1 | 2 | 3 | 4;
// 1: TICKET, 2: HITOS, 3: TAREAS, 4: TAREAS PERIÓDICAS

export interface Ticket {
  id: string;
  identificador: string;       // Ej: "TCK-1001"
  titulo: string;
  descripcion: string;
  correo: string;
  prioridad: "baja" | "media" | "alta" | "critica";
  estado: "abierto" | "en_progreso" | "resuelto" | "cerrado";
  asignar?: string | null;
  columna: ColumnaTicket;      // Default: 1
  leido: boolean;              // Default: false (true al ser abierto/leído)
  frecuencia?: Frecuencia | null; // Objeto de frecuencia o null
  imagenes: string[];
  fecha_creacion: string;      // ISO 8601 UTC
  fecha_edicion?: string | null;
}
```

---

## 2. Cartel de "NUEVO" y Estado de Lectura (`leido`)

### Comportamiento:
- Cada ticket nuevo ingresa con `leido: false`.
- En la tarjeta del ticket en el tablero/lista, si `ticket.leido === false`, renderizar un badge distintivo: **"NUEVO"**.
- Al hacer clic en la tarjeta o al abrir el modal de detalles del ticket, se debe invocar la API para marcarlo como leído (`leido = true`), removiendo el badge automáticamente.

### A. Endpoint para marcar como leído:
```http
PATCH /api/v1/tickets/{id}/read
```
- **Sin payload requerido**.
- **Respuesta (`200 OK`)**: Objeto `Ticket` con `leido: true`.

### B. Ejemplo de implementación en React:
```typescript
const handleOpenTicket = async (ticket: Ticket) => {
  // Abrir modal de detalle
  setSelectedTicket(ticket);

  // Si no está leído, marcarlo como leído en el backend
  if (!ticket.leido) {
    try {
      const res = await fetch(`${API_URL}/api/v1/tickets/${ticket.id}/read`, {
        method: "PATCH"
      });
      if (res.ok) {
        const updatedTicket = await res.json();
        // Actualizar el estado local para quitar el badge "NUEVO"
        setTickets(prev =>
          prev.map(t => (t.id === ticket.id ? { ...t, leido: true } : t))
        );
      }
    } catch (error) {
      console.error("Error marcando ticket como leído:", error);
    }
  }
};
```

### C. Filtro opcional en listado:
Si se desea mostrar un filtro de "Solo nuevos / No leídos", se puede utilizar el query param:
```http
GET /api/v1/tickets/?leido=false
```

---

## 3. Notificaciones de Escritorio y Tiempo Real (SSE)

Para evitar sobrecargar la arquitectura con Socket.IO, el backend implementa **Server-Sent Events (SSE)** nativo mediante HTTP streaming estándar. El backend emite el nuevo ticket completo en formato JSON cada vez que se crea en la base de datos. Además, envía un keep-alive `: ping\n\n` cada 15 segundos para evitar que Railway o proxies cierren la conexión.

### Endpoint SSE:
```http
GET /api/v1/tickets/stream
Content-Type: text/event-stream
```

### Implementación en React (Hook o Componente Principal):

```typescript
import { useEffect } from "react";

export const useTicketStream = (onNewTicket: (ticket: Ticket) => void) => {
  useEffect(() => {
    // 1. Solicitar permisos para notificaciones nativas de escritorio
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }

    // 2. Conectar al canal SSE nativo
    const eventSource = new EventSource(`${API_URL}/api/v1/tickets/stream`);

    eventSource.onmessage = (event) => {
      try {
        const newTicket: Ticket = JSON.parse(event.data);

        // A. Actualizar estado en la UI (agregar al tablero en su columna)
        onNewTicket(newTicket);

        // B. Disparar notificación nativa de escritorio del sistema operativo
        if ("Notification" in window && Notification.permission === "granted") {
          const notification = new Notification(`🎫 Nuevo Ticket: ${newTicket.identificador}`, {
            body: `${newTicket.titulo}\nSolicitado por: ${newTicket.correo}`,
            icon: "/logo.png" // Ruta al logo de la app
          });

          notification.onclick = () => {
            window.focus();
            // Opcional: navegar al ticket o abrir modal
          };
        }
      } catch (err) {
        console.error("Error procesando mensaje SSE:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.warn("Conexión SSE interrumpida. El navegador reconectará automáticamente.", err);
    };

    // 3. Cleanup al desmontar
    return () => {
      eventSource.close();
    };
  }, [onNewTicket]);
};
```

> 💡 **Nota**: Los navegadores manejan automáticamente la reconexión con `EventSource` si la conexión cae.

---

## 4. Soporte de Frecuencias Periódicas (`frecuencia`)

Utilizado principalmente cuando el ticket pertenece a la columna de **Tareas Periódicas** (`columna: 4`).

### Estructura de Datos:
```typescript
interface Frecuencia {
  numero: number; // Número entero >= 1
  periodo: "Días" | "Semanas" | "Meses" | "Años"; // Exactamente estos strings con mayúscula inicial y tildes
}
```
*Si el ticket no es periódico, el valor debe ser `null` o omitirse.*

---

### A. Al Crear un Ticket (`POST /api/v1/tickets/`)
El endpoint de creación utiliza `multipart/form-data` debido a la subida de imágenes.
Para enviar la frecuencia:
- Debe enviarse como un **string JSON** en el campo `frecuencia` del `FormData`.

```typescript
const formData = new FormData();
formData.append("titulo", values.titulo);
formData.append("descripcion", values.descripcion);
formData.append("correo", values.correo);
formData.append("columna", String(values.columna)); // ej: "4"

// Si tiene frecuencia configurada:
if (values.columna === 4 && values.frecuencia) {
  const frecuenciaPayload = {
    numero: Number(values.frecuencia.numero),
    periodo: values.frecuencia.periodo // "Días" | "Semanas" | "Meses" | "Años"
  };
  formData.append("frecuencia", JSON.stringify(frecuenciaPayload));
}

// Adjuntar imágenes si existen
files.forEach(file => formData.append("files", file));

const res = await fetch(`${API_URL}/api/v1/tickets/`, {
  method: "POST",
  body: formData
});
```

---

### B. Al Actualizar un Ticket (`PATCH /api/v1/tickets/{id}`)
Este endpoint utiliza `application/json`:

```typescript
const updatePayload = {
  columna: 4,
  frecuencia: {
    numero: 2,
    periodo: "Semanas"
  }
};

await fetch(`${API_URL}/api/v1/tickets/${ticketId}`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(updatePayload)
});
```
*Para remover la frecuencia, se puede enviar `"frecuencia": null`.*

---

### C. Renderizado en UI:
En la tarjeta del ticket:
```tsx
{ticket.frecuencia && (
  <span className="badge-frecuencia">
    🔄 Cada {ticket.frecuencia.numero} {ticket.frecuencia.periodo}
  </span>
)}
```

---

## 5. Resumen Rápido de Endpoints

| Método | Endpoint | Content-Type | Descripción |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/tickets/stream` | `text/event-stream` | Conexión SSE para recibir tickets en tiempo real y disparar notificaciones nativas. |
| `PATCH` | `/api/v1/tickets/{id}/read` | `application/json` | Marca el ticket como leído (`leido = true`), removiendo el cartel "NUEVO". |
| `GET` | `/api/v1/tickets/?leido=false` | — | Filtra tickets para traer únicamente los no leídos. |
| `POST` | `/api/v1/tickets/` | `multipart/form-data` | Crear ticket (admite campo `frecuencia` como string JSON y `columna: 1..4`). |
| `PATCH` | `/api/v1/tickets/{id}` | `application/json` | Actualizar campos (`columna`, `frecuencia`, `estado`, etc.). |
