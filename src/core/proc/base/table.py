from typing import Dict, List, Optional

from pyspark.sql import DataFrame, SparkSession

from core import DataOperationsFactory
from core.db.manager import DatabaseManager, Environment
from core.db.operations.interface import DataOperationsInterface


class Table:
    """
    Clase base para representar una tabla de datos en Databricks.

    Args:
        table: Nombre de la tabla.
        env: Ambiente de la base de datos (RAW, CURATED, CONSUMPTION).
        table_name: Nombre alternativo para la tabla destino. Si no se especifica,
                    se usa el mismo que `table`.
        columns: Lista de columnas a seleccionar. Por defecto selecciona todas.
        rename_map: Diccionario {nombre_original: nombre_nuevo} para renombrar columnas.
        cache_result: Si True, cachea el resultado de la lectura en memoria de Spark.
        catalog: Catálogo de Unity Catalog (default: "workspace").
    """

    def __init__(
        self,
        table: str,
        env: Environment,
        table_name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        rename_map: Optional[Dict[str, str]] = None,
        cache_result: Optional[bool] = False,
        catalog: str = "workspace",
    ):
        self.table = table
        self.env = env
        self.table_name = table_name if table_name else table
        self.columns = columns or []
        self.rename_map = rename_map
        self.cache_result = cache_result
        self.catalog = catalog
        self._df_data: Optional[DataFrame] = None
        self._db_manager: Optional[DatabaseManager] = None

    # ------------------------------------------------------------------
    # DatabaseManager
    # ------------------------------------------------------------------

    def get_db_manager(self) -> DatabaseManager:
        """Obtiene (o crea) el gestor de la base de datos."""
        if self._db_manager is None:
            self._db_manager = DatabaseManager(
                env=self.env,
                table=self.table,
                catalog=self.catalog,
            )
        return self._db_manager

    def get_table_path(self) -> str:
        """Retorna la ruta completa de la tabla (catalog.schema.table)."""
        return self.get_db_manager().get_table_path()

    # ------------------------------------------------------------------
    # Lectura de fuente
    # ------------------------------------------------------------------

    def read_source(
        self,
        data_ops: Optional[DataOperationsInterface] = None,
        session: Optional[SparkSession] = None,
    ) -> DataFrame:
        """
        Lee los datos de la tabla y aplica selección y renombrado de columnas.

        Args:
            data_ops: Instancia de operaciones de datos. Si no se provee,
                      se crea una a partir de `session`.
            session: SparkSession. Requerida si no se provee `data_ops`.

        Returns:
            DataFrame con los datos leídos.
        """
        if data_ops is None and session is not None:
            data_ops = DataOperationsFactory.create(session)
        elif data_ops is None:
            raise ValueError("Se debe proporcionar una sesión o un objeto DataOperationsFactory.")

        # Retornar resultado cacheado si corresponde
        if self._df_data is not None and self.cache_result:
            return self._df_data

        df = data_ops.table_input(table_name=self.get_table_path())

        if self.columns:
            df = df.select(*self.columns)

        if self.rename_map:
            for original, new_name in self.rename_map.items():
                df = df.withColumnRenamed(original, new_name)

        self._df_data = df.cache() if self.cache_result else df
        return self._df_data

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def table_has_data(
        self,
        data_ops: Optional[DataOperationsInterface] = None,
        session: Optional[SparkSession] = None,
    ) -> bool:
        """
        Verifica si la tabla tiene datos.

        Returns:
            True si la tabla tiene al menos un registro.
        """
        return self.read_source(data_ops=data_ops, session=session).count() > 0

    def check_and_fix_streams(
        self,
        data_ops: Optional[DataOperationsInterface] = None,
        session: Optional[SparkSession] = None,
    ) -> dict:
        """
        No-op informativo.

        En Databricks, la replicación y el CDC se manejan de forma nativa
        mediante Delta Lake y Structured Streaming. No se requieren streams
        manuales de Snowflake.

        Returns:
            Dict con estado de éxito.
        """
        return {
            "stale": False,
            "created": False,
            "message": (
                "Streams de Snowflake no aplican en Databricks. "
                "Utiliza Delta Lake Change Data Feed o Structured Streaming."
            ),
        }
