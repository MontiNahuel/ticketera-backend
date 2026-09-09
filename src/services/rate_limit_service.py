from datetime import datetime, timezone, timedelta
from ..models.ticket_model import Ticket
from ..core.exceptions import BadRequestException
from ..config.settings import settings

class RateLimitService:
    def __init__(self):
        self.max_daily_tickets: int = settings.MAX_DAILY_TICKETS_PER_EMAIL
        self.cooldown_seconds: int = settings.TICKET_CREATION_COOLDOWN_SECONDS

    async def validate_ticket_creation(self, correo: str) -> None:
        """
        Valida que el solicitante (correo):
        1. No esté dentro del periodo de enfriamiento / cooldown (60 seg por defecto).
        2. No supere el límite de tickets diarios permitidos (8 por defecto).
        """
        if not correo:
            return

        correo_limpio = correo.strip().lower()

        # Los administradores en la lista blanca quedan exentos de cooldown y límite diario
        admin_emails = [admin.strip().lower() for admin in settings.ADMIN_EMAILS]
        if correo_limpio in admin_emails:
            return

        ahora = datetime.now(timezone.utc)
        limite_24h = ahora - timedelta(hours=24)

        # 1. Validar Cooldown Anti-Spam
        ultimo_ticket = await Ticket.find(
            Ticket.correo == correo_limpio
        ).sort("-fecha_creacion").limit(1).first_or_none()

        if ultimo_ticket and ultimo_ticket.fecha_creacion:
            fecha_ticket = ultimo_ticket.fecha_creacion
            if fecha_ticket.tzinfo is None:
                fecha_ticket = fecha_ticket.replace(tzinfo=timezone.utc)

            tiempo_transcurrido = (ahora - fecha_ticket).total_seconds()
            if tiempo_transcurrido < self.cooldown_seconds:
                segundos_restantes = int(self.cooldown_seconds - tiempo_transcurrido)
                raise BadRequestException(
                    f"Por favor espera {segundos_restantes} segundos antes de enviar otro ticket (Anti-Spam)."
                )

        # 2. Validar Límite Diario (últimas 24 horas)
        tickets_en_24h = await Ticket.find(
            Ticket.correo == correo_limpio,
            Ticket.fecha_creacion >= limite_24h
        ).count()

        if tickets_en_24h >= self.max_daily_tickets:
            raise BadRequestException(
                f"Has alcanzado el límite máximo diario de {self.max_daily_tickets} tickets para el correo '{correo_limpio}'."
            )
