from typing import List, Optional
from datetime import datetime, timezone
from fastapi import Depends, UploadFile
from beanie import PydanticObjectId
from pymongo import ReturnDocument
from ..repositories.ticket_repository import TicketRepository
from ..schemas.ticket_schema import TicketCreate, TicketUpdate, TicketResponse
from ..models.ticket_model import Ticket
from ..core.exceptions import NotFoundException
from ..core.sse_manager import sse_manager
from .rate_limit_service import RateLimitService

class TicketService:
    def __init__(
        self,
        repository: TicketRepository = Depends(),
        rate_limit_service: RateLimitService = Depends()
    ):
        self.repository = repository
        self.rate_limit_service = rate_limit_service

    async def _generate_next_identifier(self) -> str:
        """
        Genera un identificador secuencial atómico (TCK-1001, TCK-1002, ...)
        usando find_one_and_update en la colección 'counters' de MongoDB.
        Es seguro ante concurrencia y no colisiona si se eliminan tickets.
        """
        db = Ticket.get_pymongo_collection().database
        counter_col = db["counters"]

        # 1. Asegurar que el contador esté sincronizado con el identificador más alto existente
        existing_counter = await counter_col.find_one({"_id": "ticket_seq"})
        if not existing_counter:
            start_seq = 1000
            last_ticket = await Ticket.find_all().sort("-identificador").limit(1).to_list()
            if last_ticket and last_ticket[0].identificador:
                try:
                    num_part = int(last_ticket[0].identificador.split("-")[-1])
                    if num_part >= start_seq:
                        start_seq = num_part
                except (ValueError, IndexError):
                    pass

            await counter_col.update_one(
                {"_id": "ticket_seq"},
                {"$set": {"seq": start_seq}},
                upsert=True
            )

        # 2. Incrementar atómicamente
        counter = await counter_col.find_one_and_update(
            {"_id": "ticket_seq"},
            {"$inc": {"seq": 1}},
            return_document=ReturnDocument.AFTER
        )
        return f"TCK-{counter['seq']}"

    async def get_all_tickets(
        self,
        filters: Optional[dict] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Ticket]:
        if filters:
            return await self.repository.get_filtered(filters=filters, skip=skip, limit=limit)
        return await self.repository.get_all(skip=skip, limit=limit)

    async def get_ticket(self, id: PydanticObjectId) -> Ticket:
        ticket = await self.repository.get(id)
        if not ticket:
            raise NotFoundException(f"Ticket con id {id} no encontrado")
        return ticket

    async def create_ticket(self, ticket_in: TicketCreate) -> Ticket:
        # Validar Rate Limit y Cooldown
        await self.rate_limit_service.validate_ticket_creation(ticket_in.correo)

        identificador = await self._generate_next_identifier()
        
        ticket_data = ticket_in.model_dump()
        ticket_data["identificador"] = identificador
        
        ticket = Ticket(**ticket_data)
        return await ticket.insert()

    async def create_ticket_with_rollback(
        self,
        ticket_in: TicketCreate,
        files: Optional[List[UploadFile]] = None,
        gridfs_service = None
    ) -> Ticket:
        # Validar Rate Limit y Cooldown ANTES de subir archivos a GridFS
        await self.rate_limit_service.validate_ticket_creation(ticket_in.correo)

        uploaded_ids = []
        created_ticket = None
        try:
            # 1. Subir archivos si fueron provistos
            if files and gridfs_service:
                for file in files:
                    if file.filename:
                        fid = await gridfs_service.upload_file(file)
                        uploaded_ids.append(fid)

            # 2. Armar lista de imágenes
            image_urls = [f"/api/v1/files/{fid}" for fid in uploaded_ids]
            if ticket_in.imagenes:
                image_urls.extend(ticket_in.imagenes)

            identificador = await self._generate_next_identifier()

            ticket_data = ticket_in.model_dump()
            ticket_data["identificador"] = identificador
            ticket_data["imagenes"] = image_urls

            # 3. Guardar el documento Ticket en MongoDB
            created_ticket = Ticket(**ticket_data)
            saved_ticket = await created_ticket.insert()

            # 4. Notificar a las pantallas conectadas vía SSE
            try:
                ticket_resp = TicketResponse.model_validate(saved_ticket)
                await sse_manager.broadcast("nuevo_ticket", ticket_resp.model_dump(mode="json"))
            except Exception:
                pass

            return saved_ticket

        except Exception as exc:
            # --- ROLLBACK AUTOMÁTICO EN EL BACKEND ---
            if gridfs_service:
                for fid in uploaded_ids:
                    try:
                        await gridfs_service.delete_file(fid)
                    except Exception:
                        pass
            if created_ticket and hasattr(created_ticket, "id") and created_ticket.id:
                try:
                    await created_ticket.delete()
                except Exception:
                    pass
            raise exc

    async def mark_as_read(self, id: PydanticObjectId) -> Ticket:
        ticket = await self.get_ticket(id)
        ticket.leido = True
        await ticket.save()
        return ticket

    async def update_ticket(self, id: PydanticObjectId, ticket_in: TicketUpdate) -> Ticket:
        ticket = await self.repository.update(id, ticket_in)
        if not ticket:
            raise NotFoundException(f"Ticket con id {id} no encontrado")
        return ticket

    async def add_image_to_ticket(self, id: PydanticObjectId, image_id_or_url: str) -> Ticket:
        return await self.add_images_to_ticket(id, [image_id_or_url])

    async def add_images_to_ticket(self, id: PydanticObjectId, image_urls: List[str]) -> Ticket:
        ticket = await self.get_ticket(id)
        modified = False
        for url in image_urls:
            if url not in ticket.imagenes:
                ticket.imagenes.append(url)
                modified = True
        if modified:
            ticket.fecha_edicion = datetime.now(timezone.utc)
            await ticket.save()
        return ticket

    async def remove_image_from_ticket(
        self,
        id: PydanticObjectId,
        file_id: str,
        gridfs_service = None
    ) -> Ticket:
        ticket = await self.get_ticket(id)
        
        # Buscar la URL correspondiente
        target_url = f"/api/v1/files/{file_id}"
        found = False
        new_imagenes = []
        for img in ticket.imagenes:
            if img == target_url or file_id in img:
                found = True
            else:
                new_imagenes.append(img)
                
        if not found:
            raise NotFoundException(f"La imagen {file_id} no está asociada a este ticket")
            
        ticket.imagenes = new_imagenes
        ticket.fecha_edicion = datetime.now(timezone.utc)
        await ticket.save()
        
        # Eliminar físicamente de GridFS para liberar espacio
        if gridfs_service:
            try:
                await gridfs_service.delete_file(file_id)
            except Exception:
                pass
                
        return ticket

    async def delete_ticket(self, id: PydanticObjectId, gridfs_service = None) -> bool:
        ticket = await self.get_ticket(id)
        
        # Eliminar todas sus imágenes de GridFS
        if gridfs_service and ticket.imagenes:
            for img_url in ticket.imagenes:
                try:
                    file_id = img_url.split("/")[-1]
                    await gridfs_service.delete_file(file_id)
                except Exception:
                    pass

        success = await self.repository.delete(id)
        if not success:
            raise NotFoundException(f"Ticket con id {id} no encontrado")
        return True
