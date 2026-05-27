"""
Utilidades para el manejo de nombres en Unity Catalog de Databricks.

Modelo de 3 niveles: catalog.schema.table
- En producción: workspace.raw / workspace.curated / workspace.consumption
- En desarrollo: workspace.{user}_raw / workspace.{user}_curated  (aislado por usuario)
"""

import os
from enum import Enum
from typing import Optional


class Environment(str, Enum):
    """
    Ambientes de datos disponibles.

    Attributes:
        RAW: Datos crudos (ingesta)
        CURATED: Datos curados (transformados)
        CONSUMPTION: Datos de consumo (modelo estrella / reportes)
    """

    RAW = "raw"
    CURATED = "curated"
    CONSUMPTION = "consumption"


def _dev_user_prefix() -> Optional[str]:
    """
    Retorna el prefijo de usuario para entornos de desarrollo.

    Lee la variable de entorno DATABRICKS_DEV_USER.
    Si no está definida, intenta obtenerla del contexto de Databricks.
    """
    user = os.getenv("DATABRICKS_DEV_USER")
    if user:
        # sanitizar: quitar dominio de email y caracteres no alfanuméricos
        return user.split("@")[0].replace(".", "_").replace("-", "_").lower()
    return None


class DatabaseManager:
    """
    Gestiona la nomenclatura de tablas en Unity Catalog de Databricks.

    Construye rutas del tipo  catalog.schema.table  donde el nombre del
    esquema refleja el ambiente (raw / curated / consumption) y, en
    desarrollo, añade el prefijo del usuario para aislar los datos.

    Examples:
        # Producción  →  workspace.curated.dt_tipo_documento
        db = DatabaseManager(Environment.CURATED, "dt_tipo_documento")
        db.get_table_path()

        # Desarrollo  →  workspace.rbeauxisconsultor_curated.dt_tipo_documento
        # (cuando DATABRICKS_DEV_USER=rbeauxisconsultor@gmail.com y IS_DEV=true)
    """

    IS_DEV: bool = os.getenv("ENTORNO_LOCAL", "False").lower() == "true"

    def __init__(
        self,
        env: Environment,
        schema: Optional[str] = None,
        table: Optional[str] = None,
        catalog: str = "workspace",
    ) -> None:
        """
        Args:
            env: Ambiente (RAW, CURATED, CONSUMPTION)
            schema: Nombre del esquema lógico dentro del ambiente (ej. "master").
                    Si se omite, el esquema del Unity Catalog será solo el ambiente.
            table: Nombre de la tabla por defecto.
            catalog: Catálogo de Unity Catalog (default: "workspace").
        """
        self.env = env
        self.schema = schema
        self.table = table
        self.catalog = catalog

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _uc_schema(self) -> str:
        """
        Construye el nombre del esquema en Unity Catalog.

        En producción:   <env>          → curated
        En desarrollo:   <user>_<env>   → rbeauxisconsultor_curated
        """
        env_name = self.env.value
        if self.IS_DEV:
            prefix = _dev_user_prefix()
            if prefix:
                return f"{prefix}_{env_name}"
        return env_name

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get_schema_path(self, schema: Optional[str] = None) -> str:
        """
        Ruta hasta el esquema: catalog.uc_schema

        Args:
            schema: si se proporciona, se ignora (Unity Catalog no tiene
                    sub-esquemas; este parámetro se mantiene por compatibilidad).
        """
        return f"{self.catalog}.{self._uc_schema()}"

    def get_table_path(self, schema: Optional[str] = None, table: Optional[str] = None) -> str:
        """
        Ruta completa a la tabla: catalog.uc_schema.table

        Args:
            schema: ignorado (mantenido por compatibilidad con el código existente).
            table: nombre de la tabla. Si se omite, usa el del constructor.

        Raises:
            ValueError: Si no se especifica una tabla.
        """
        table_name = table or self.table
        if not table_name:
            raise ValueError("Tabla no especificada.")
        return f"{self.get_schema_path()}.{table_name}"


# ---------------------------------------------------------------------------
# Uso de ejemplo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    for env in Environment:
        db = DatabaseManager(env, table="ejemplo")
        print(f"{env.value}: {db.get_table_path()}")
