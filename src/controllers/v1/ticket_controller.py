from fastapi import APIRouter, Depends, status, UploadFile, File, Form, Query
from typing import List, Optional, Union
from datetime import datetime
from pydantic import EmailStr
from beanie import PydanticObjectId
from ...schemas.ticket_schema import TicketCreate, TicketUpdate, TicketResponse
from ...models.ticket_model import PrioridadEnum, EstadoEnum
from ...services.ticket_service import TicketService
from ...services.gridfs_service import GridFSService

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED, summary="Crear un ticket con texto e imágenes opcionales (Con Rollback)")
async def create_ticket(
    titulo: str = Form(..., min_length=3, max_length=150, description="Título del problema"),
    descripcion: str = Form(..., description="Descripción detallada"),
    correo: EmailStr = Form(..., description="Correo del solicitante"),
    prioridad: PrioridadEnum = Form(PrioridadEnum.MEDIA, description="Prioridad del ticket"),
    asignar: Optional[str] = Form(None, description="Técnico asignado (opcional)"),
    columna: Optional[int] = Form(1, description="Columna del ticket (1: Ticket, 2: Hitos, 3: Tareas, 4: Tareas periódicas)"),
    files: List[UploadFile] = File(default=[], description="Solo archivos de imagen permitidos (PNG, JPEG, WebP, GIF, SVG)"),
    service: TicketService = Depends(),
    gridfs_service: GridFSService = Depends()
):
    ticket_in = TicketCreate(
        titulo=titulo,
        descripcion=descripcion,
        correo=correo,
        prioridad=prioridad,
        asignar=asignar,
        columna=columna or 1
    )
    # Filtrar solo archivos válidos con nombre
    valid_files = [f for f in files if getattr(f, "filename", None)]

    return await service.create_ticket_with_rollback(
        ticket_in=ticket_in,
        files=valid_files if valid_files else None,
        gridfs_service=gridfs_service
    )

@router.get("/", response_model=List[TicketResponse], summary="Listar tickets con filtros y paginación")
async def get_tickets(
    fecha_desde: Optional[str] = Query(None, description="Fecha de inicio flexible (ej: 2026-08-01 o 2026-08-01T14:30:00)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha fin flexible (ej: 2026-08-31 o 2026-08-31T23:59:59)"),
    estado: Optional[EstadoEnum] = Query(None, description="Filtrar por estado del ticket"),
    prioridad: Optional[PrioridadEnum] = Query(None, description="Filtrar por prioridad"),
    asignar: Optional[str] = Query(None, description="Filtrar por técnico/usuario asignado"),
    columna: Optional[int] = Query(None, ge=1, le=4, description="Filtrar por columna (1, 2, 3, 4)"),
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros a devolver"),
    service: TicketService = Depends()
):
    filters = {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "estado": estado,
        "prioridad": prioridad,
        "asignar": asignar,
        "columna": columna
    }
    clean_filters = {k: v for k, v in filters.items() if v is not None}
    return await service.get_all_tickets(
        filters=clean_filters if clean_filters else None,
        skip=skip,
        limit=limit
    )

@router.get("/{id}", response_model=TicketResponse, summary="Obtener ticket por ID")
async def get_ticket(id: PydanticObjectId, service: TicketService = Depends()):
    return await service.get_ticket(id)

@router.patch("/{id}", response_model=TicketResponse, summary="Actualizar ticket por ID (PATCH)")
async def update_ticket(id: PydanticObjectId, ticket_in: TicketUpdate, service: TicketService = Depends()):
    return await service.update_ticket(id, ticket_in)

@router.post("/{id}/images", response_model=TicketResponse, summary="Adjuntar una o varias imágenes a un ticket mediante GridFS")
async def upload_ticket_images(
    id: PydanticObjectId,
    files: List[UploadFile] = File(..., description="Selecciona archivos de imagen permitidos (PNG, JPEG, WebP, GIF, SVG)"),
    ticket_service: TicketService = Depends(),
    gridfs_service: GridFSService = Depends()
):
    file_ids = await gridfs_service.upload_files(files)
    image_urls = [f"/api/v1/files/{fid}" for fid in file_ids]
    return await ticket_service.add_images_to_ticket(id, image_urls)

@router.delete("/{id}/images/{file_id}", response_model=TicketResponse, summary="Eliminar una imagen específica de un ticket y borrarla de GridFS")
async def delete_ticket_image(
    id: PydanticObjectId,
    file_id: str,
    ticket_service: TicketService = Depends(),
    gridfs_service: GridFSService = Depends()
):
    return await ticket_service.remove_image_from_ticket(id, file_id, gridfs_service)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar ticket por ID y todas sus fotos asociadas")
async def delete_ticket(
    id: PydanticObjectId,
    service: TicketService = Depends(),
    gridfs_service: GridFSService = Depends()
):
    await service.delete_ticket(id, gridfs_service)
