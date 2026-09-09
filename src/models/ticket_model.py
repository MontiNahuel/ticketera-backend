from enum import Enum
from typing import Optional, List, Literal
from datetime import datetime, timezone
from beanie import Document, Indexed
from pydantic import BaseModel, Field, EmailStr

class Frecuencia(BaseModel):
    numero: int = Field(default=1, ge=1, description="Intervalo numérico")
    periodo: Literal["Días", "Semanas", "Meses", "Años"] = Field(..., description="Período de repetición")

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
    leido: bool = Field(default=False, description="Indica si el ticket ya fue abierto/leído por el equipo")
    frecuencia: Optional[Frecuencia] = Field(default=None, description="Frecuencia periódica de repetición si aplica")

    class Settings:
        name = "tickets"

