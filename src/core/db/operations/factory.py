from typing import Any, Dict, Type

from core.db.operations.databricks import DatabricksOperations
from core.db.operations.interface import DataOperationsInterface


class DataOperationsFactory:
    """Factory para crear instancias de operaciones de datos."""

    _implementations: Dict[str, Type[DataOperationsInterface]] = {
        "databricks": DatabricksOperations,
    }

    @classmethod
    def create(cls, session: Any, engine_type: str = "databricks") -> DataOperationsInterface:
        """Crea una instancia de operaciones de datos del tipo especificado.

        Args:
            session: SparkSession activa.
            engine_type: Tipo de motor ('databricks' por defecto).

        Returns:
            Instancia de DataOperationsInterface.

        Raises:
            ValueError: Si el tipo de motor no está soportado.
        """
        implementation = cls._implementations.get(engine_type)
        if not implementation:
            raise ValueError(
                f"Engine type '{engine_type}' not supported. "
                f"Available: {list(cls._implementations.keys())}"
            )
        return implementation(session)
