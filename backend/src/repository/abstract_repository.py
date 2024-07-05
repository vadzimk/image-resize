import uuid
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Any, Dict

from odmantic import Model


class AbstractRepository(ABC):
    @abstractmethod
    async def add(self, project: Model) -> Model:
        raise NotImplementedError()

    @abstractmethod
    async def get(self, filters: Dict[str, Any]) -> Model:
        raise NotImplementedError()

    @abstractmethod
    async def update(self, filters: Dict[str, Any], update: Dict) -> Model:
        raise NotImplementedError()

    @abstractmethod
    async def list(self,
                   skip: Optional[int] = 0,
                   limit: Optional[int] = None,
                   sort: Optional[List[Tuple[str, Any]]] = None,
                   filters: Optional[Dict[str, Any]] = None) -> List[Model]:
        raise NotImplementedError()
