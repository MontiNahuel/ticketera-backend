from typing import List
from ..schemas.catalog_schema import OptionItem
from ..models.ticket_model import PrioridadEnum, EstadoEnum

class CatalogService:
    def get_estados(self) -> List[OptionItem]:
        estado_labels = {
            EstadoEnum.ABIERTO: "Abierto",
            EstadoEnum.EN_PROGRESO: "En Progreso",
            EstadoEnum.RESUELTO: "Resuelto",
            EstadoEnum.CERRADO: "Cerrado"
        }
        return [
            OptionItem(value=e.value, label=estado_labels.get(e, e.value.replace("_", " ").title()))
            for e in EstadoEnum
        ]

    def get_prioridades(self) -> List[OptionItem]:
        prioridad_labels = {
            PrioridadEnum.BAJA: "Baja",
            PrioridadEnum.MEDIA: "Media",
            PrioridadEnum.ALTA: "Alta",
            PrioridadEnum.CRITICA: "Crítica"
        }
        return [
            OptionItem(value=p.value, label=prioridad_labels.get(p, p.value.title()))
            for p in PrioridadEnum
        ]

    async def get_asignables(self) -> List[OptionItem]:
        return [
            OptionItem(value="facundo_bernard", label="Facundo Bernard"),
            OptionItem(value="nicolas_fernandez", label="Nicolas Fernandez"),
            OptionItem(value="nahuel_monti", label="Nahuel Monti")
        ]

