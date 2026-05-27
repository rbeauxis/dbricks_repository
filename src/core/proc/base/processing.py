from abc import ABC
from typing import Dict, List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp

from core import DataOperationsFactory
from core.db.operations.interface import DataOperationsInterface
from core.proc.base.table import Table


class BaseProcessing(ABC):
    """
    Clase base abstracta para el procesamiento de datos en Databricks.

    Implementa un framework ETL de 12 pasos estandarizados (del paso _00_ al _11_)
    que las clases hijas pueden extender y personalizar según las necesidades de negocio.

    Las clases hijas deben implementar al menos _04_transform y upsert_merge_keys.
    Los demás métodos tienen implementaciones por defecto que pueden ser sobrescritos.
    """

    def __init__(
        self,
        session: SparkSession,
        destination: Table,
        sources: Optional[List[Table]] = None,
    ) -> None:
        """
        Inicializa el procesador de datos.

        Args:
            session: SparkSession activa de Databricks.
            destination: Objeto Table que representa la tabla de destino.
            sources: Lista de objetos Table que representan las fuentes de datos.
        """
        self.session = session
        self.data_ops: DataOperationsInterface = DataOperationsFactory.create(session)
        self.sources = sources or []
        self.destination = destination

    # ==================================================================
    # MÉTODO PRINCIPAL DE EJECUCIÓN
    # ==================================================================

    def run(self) -> None:
        """
        Ejecuta el flujo completo de procesamiento de datos en 12 pasos:

          [00] Obtener tablas adicionales de fuentes dinámicas
          [01] Leer fuentes de datos
          [02] Aplicar filtros previos al join
          [03] Unir las fuentes (join)
          [04] Transformar los datos
          [05] Agregar fila con valores por defecto
          [06] Agregar columna de timestamp de modificación
          [07] Agregar columnas por defecto adicionales
          [08] Determinar si la operación es solo inserción
          [09] Upsert (merge) o inserción simple
          [10] Escritura directa a tabla (si es solo insert)
          [11] Proceso posterior al guardado
        """
        dict_tables_temp = self._00_get_tables()
        for source in self.sources:
            dict_tables_temp[source.table_name] = source
        self.sources = list(dict_tables_temp.values())

        self.df_sources_dict = self._01_read_source(self.sources)
        self.df_sources_dict = self._02_pre_filter(self.df_sources_dict)
        joined_df = self._03_join(self.df_sources_dict)
        transformed_df = self._04_transform(joined_df)
        transformed_df = self._05_add_default_row(transformed_df)
        transformed_df = self._06_add_modification_timestamp(transformed_df)
        transformed_df = self._07_add_default_column(transformed_df)

        if not self._08_is_only_insert():
            self._09_upsert(transformed_df)
        else:
            self._10_table_output(transformed_df)

        self._11_post_save_process(self.destination)

    # ==================================================================
    # PASOS DEL FRAMEWORK (sobreescribibles por las clases hijas)
    # ==================================================================

    def _00_get_tables(self) -> Dict[str, Table]:
        """[00] Retorna fuentes de datos adicionales definidas dinámicamente."""
        return {}

    def _01_read_source(self, sources: List[Table]) -> Dict[str, DataFrame]:
        """[01] Lee los datos de las fuentes especificadas.

        Returns:
            Diccionario {table_name: DataFrame}.
        """
        return {table.table_name: table.read_source(self.data_ops) for table in sources}

    def _02_pre_filter(self, df_sources_dict: Dict[str, DataFrame]) -> Dict[str, DataFrame]:
        """[02] Aplica filtros previos a la operación de join.

        Por defecto retorna los DataFrames sin modificación.
        Las clases hijas pueden sobrescribir este método para filtrar datos
        antes del join.
        """
        return df_sources_dict

    def _03_join(self, df_sources_dict: Dict[str, DataFrame]) -> DataFrame:
        """[03] Realiza la operación de join entre las fuentes.

        Por defecto retorna la primera fuente sin realizar joins.
        Las clases hijas deben sobrescribir este método cuando necesiten
        combinar múltiples fuentes.
        """
        return df_sources_dict[self.sources[0].table_name]

    def _04_transform(self, joined_df: DataFrame) -> DataFrame:
        """[04] Aplica transformaciones a los datos después del join.

        Método principal que deben sobrescribir las clases hijas para
        implementar la lógica de transformación del negocio.
        Por defecto retorna el DataFrame sin modificación.
        """
        return joined_df

    def _05_add_default_row(self, transformed_df: DataFrame) -> DataFrame:
        """[05] Agrega una fila con valores por defecto al DataFrame.

        Útil para representar valores nulos o desconocidos en dimensiones.
        Por defecto agrega un DataFrame vacío con el mismo schema (sin filas).
        Las clases hijas pueden sobrescribir para definir la fila por defecto.
        """
        empty_df = self.session.createDataFrame([], schema=transformed_df.schema)
        return transformed_df.union(empty_df)

    def _06_add_modification_timestamp(self, transformed_df: DataFrame) -> DataFrame:
        """[06] Agrega la columna 'fecha_modif' con el timestamp actual."""
        return transformed_df.withColumn("fecha_modif", current_timestamp())

    def _07_add_default_column(self, transformed_df: DataFrame) -> DataFrame:
        """[07] Agrega columnas adicionales con valores por defecto.

        Las clases hijas pueden sobrescribir para agregar columnas específicas.
        """
        return transformed_df

    def _08_is_only_insert(self) -> bool:
        """[08] Determina si la operación es solo inserción (sin actualizaciones).

        Returns:
            True → solo insertar (paso _10_).
            False → hacer upsert/merge (paso _09_).
        """
        return False

    def _09_upsert(self, transformed_df: DataFrame, merge_keys: Optional[List[str]] = None) -> None:
        """[09] Realiza un MERGE (upsert) contra la tabla destino.

        Args:
            transformed_df: DataFrame con los datos a insertar/actualizar.
            merge_keys: Claves de merge. Si no se proveen, se usa upsert_merge_keys().

        Raises:
            ValueError: Si no se definen claves para el merge.
        """
        keys = merge_keys or self.upsert_merge_keys()
        if not keys:
            raise ValueError("No se han definido claves para el merge.")

        update_cols = self.upsert_update_cols() or None
        insert_cols = self.upsert_insert_cols() or None

        self.data_ops.merge_upsert(
            source_df=transformed_df,
            target_table_path=self.destination.get_table_path(),
            merge_keys=keys,
            update_columns=update_cols,
            insert_columns=insert_cols,
        )

    def _10_table_output(self, transformed_df: DataFrame, mode: Optional[str] = None) -> None:
        """[10] Escribe los datos transformados en la tabla de destino (solo inserción)."""
        self.data_ops.table_output(
            df=transformed_df,
            table_path=self.destination.get_table_path(),
            mode=mode or self.table_output_mode(),
        )

    def _11_post_save_process(self, destination: Table) -> None:
        """[11] Realiza operaciones adicionales después de guardar los datos.

        Las clases hijas pueden sobrescribir para ejecutar lógica posterior
        al guardado (ej. actualizar metadatos, notificar, limpiar temporales).
        """
        pass

    # ==================================================================
    # CONFIGURACIÓN SOBREESCRIBIBLE POR LAS CLASES HIJAS
    # ==================================================================

    def upsert_merge_keys(self) -> List[str]:
        """Define las columnas clave para la operación de merge/upsert.

        Las clases hijas deben sobrescribir este método para especificar
        las columnas que identifican de manera única un registro.
        """
        return []

    def upsert_update_cols(self) -> Dict[str, str]:
        """Define las columnas a actualizar durante un upsert.

        Returns:
            {col_destino: "source.col_fuente"} o {} para actualizar todas.
        """
        return {}

    def upsert_insert_cols(self) -> Dict[str, str]:
        """Define las columnas a insertar durante un upsert.

        Returns:
            {col_destino: "source.col_fuente"} o {} para insertar todas.
        """
        return {}

    def table_output_mode(self) -> str:
        """Define el modo de escritura para la operación de salida a tabla.

        Returns:
            'append' por defecto. Las clases hijas pueden retornar 'overwrite'.
        """
        return "append"
