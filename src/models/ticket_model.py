from enum import Enum
from typing import Optional, List
from datetime import datetime, timezone
from beanie import Document, Indexed
from pydantic import Field, EmailStr

class PrioridadEnum(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"

class EstadoEnum(str, Enum):
    ABIERTO = "abierto"
    EN_PROGRESO = "en_progreso"
    RESUELTO = "resuelto"
    CERRADO = "cerrado"

class Ticket(Document):
    titulo: str = Field(..., min_length=3, max_length=150)
    descripcion: str
    imagenes: List[str] = Field(default_factory=list)
    asignar: Optional[str] = Field(default=None)
    fecha_creacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fecha_edicion: Optional[datetime] = Field(default=None)
    identificador: Indexed(str, unique=True, sparse=True)
    correo: EmailStr
    prioridad: PrioridadEnum = Field(default=PrioridadEnum.MEDIA)
    estado: EstadoEnum = Field(default=EstadoEnum.ABIERTO)
    columna: int = Field(default=1, ge=1, le=4, description="ID numérico de la columna (1: Ticket, 2: Hitos, 3: Tareas, 4: Tareas periódicas)")

    class Settings:
        name = "tickets"
