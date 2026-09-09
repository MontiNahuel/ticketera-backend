import asyncio
import json
import logging
from typing import Set, Dict, Any

logger = logging.getLogger(__name__)

class SSEManager:
    """
    Gestor de conexiones en tiempo real para Server-Sent Events (SSE).
    Mantiene colas asíncronas para cada cliente conectado (navegador)
    y permite hacer broadcast instantáneo de nuevos tickets o eventos.
    """
    def __init__(self):
        self.listeners: Set[asyncio.Queue] = set()

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self.listeners.add(queue)
        logger.debug(f"[SSE] Nuevo suscriptor conectado. Total activos: {len(self.listeners)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self.listeners.discard(queue)
        logger.debug(f"[SSE] Suscriptor desconectado. Total activos: {len(self.listeners)}")

    async def broadcast(self, event: str, data: Dict[str, Any]) -> None:
        """
        Envía un evento a todas las pantallas/clientes conectados.
        """
        if not self.listeners:
            return

        payload = {
            "event": event,
            "data": data
        }
        for queue in list(self.listeners):
            try:
                await queue.put(payload)
            except Exception as e:
                logger.warning(f"[SSE] Error al enviar mensaje a listener: {e}")

sse_manager = SSEManager()
