from typing import List, Dict, Any
from .base_repository import BaseRepository
from ..models.ticket_model import Ticket
from ..schemas.ticket_schema import TicketCreate, TicketUpdate
from ..core.date_utils import parse_date_filter

class TicketRepository(BaseRepository[Ticket, TicketCreate, TicketUpdate]):
    def __init__(self):
        super().__init__(model=Ticket)

    async def get_filtered(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 100
    ) -> List[Ticket]:
        query = {}
        
        if filters.get("estado"):
            query["estado"] = filters["estado"]
            
        if filters.get("prioridad"):
            query["prioridad"] = filters["prioridad"]
            
        if filters.get("columna"):
            query["columna"] = filters["columna"]
            
        if "leido" in filters and filters["leido"] is not None:
            query["leido"] = filters["leido"]
            
        if filters.get("asignar"):
            query["asignar"] = {"$regex": filters["asignar"], "$options": "i"}
            
        fecha_desde_parsed = parse_date_filter(filters.get("fecha_desde"), is_end_date=False)
        fecha_hasta_parsed = parse_date_filter(filters.get("fecha_hasta"), is_end_date=True)

        if fecha_desde_parsed or fecha_hasta_parsed:
            fecha_query = {}
            if fecha_desde_parsed:
                fecha_query["$gte"] = fecha_desde_parsed
            if fecha_hasta_parsed:
                fecha_query["$lte"] = fecha_hasta_parsed
            query["fecha_creacion"] = fecha_query

        return await self.model.find(query).sort("-fecha_creacion").skip(skip).limit(limit).to_list()
