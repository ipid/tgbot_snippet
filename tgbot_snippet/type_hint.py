__all__ = ('JSON', 'WorkerTask')

import asyncio
from typing import Dict, Any, Tuple

JSON = Dict[str, Any]
WorkerTask = Tuple[str, JSON, asyncio.Future]
