"""
Command Pattern — interfaz base.
Cada acción del usuario es un Command que encapsula:
  - datos necesarios (payload)
  - validación
  - ejecución
El Orchestrator recibe commands y los ejecuta.
"""
from abc import ABC, abstractmethod


class Command(ABC):
    """Interfaz que todo command debe implementar."""

    @abstractmethod
    def validate(self) -> None:
        """Valida que el command puede ejecutarse. Lanza excepción si no."""
        ...

    @abstractmethod
    def execute(self) -> dict:
        """Ejecuta el command y retorna el resultado."""
        ...


class CommandError(Exception):
    """Error controlado durante la ejecución de un command."""
    pass
