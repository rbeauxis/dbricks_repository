from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union

from pyspark.sql import DataFrame


class DataOperationsInterface(ABC):
    """Interface base para operaciones de datos sobre PySpark / Delta Lake."""

    @abstractmethod
    def table_input(self, table_name: str, columns: Optional[List[str]] = None) -> DataFrame:
        """Lee datos de una tabla.

        Args:
            table_name: Nombre completo de la tabla (catalog.schema.table).
            columns: Lista de columnas a seleccionar. Por defecto selecciona todas.

        Returns:
            DataFrame con los datos leídos.
        """

    @abstractmethod
    def table_output(
        self,
        df: DataFrame,
        table_path: str,
        mode: str = "append",
    ) -> None:
        """Escribe datos en una tabla Delta.

        Args:
            df: DataFrame a escribir.
            table_path: Nombre completo de la tabla destino.
            mode: Modo de escritura ('overwrite', 'append', 'ignore', 'errorifexists').
        """

    @abstractmethod
    def delete_from_table(
        self,
        source_path: str,
        table_path: str,
        key_columns: Dict[str, str],
    ) -> None:
        """Borra registros de la tabla usando un merge con una fuente de deletes.

        Args:
            source_path: Tabla/vista que contiene los registros a borrar.
            table_path: Tabla destino (Delta).
            key_columns: Diccionario {columna_destino: columna_fuente} para el join.
        """

    @abstractmethod
    def filter_rows(self, df: DataFrame, condition: str) -> DataFrame:
        """Filtra filas según una condición SQL.

        Args:
            df: DataFrame de entrada.
            condition: Condición SQL (ej. "id > 1").

        Returns:
            DataFrame filtrado.
        """

    @abstractmethod
    def select_values(
        self, df: DataFrame, transformations: Dict[str, Union[str, Dict[str, str]]]
    ) -> DataFrame:
        """Selecciona y transforma columnas.

        Args:
            df: DataFrame de entrada.
            transformations: Dict donde la clave es el nombre destino y el valor:
                - str → nombre de la columna origen.
                - Dict con 'expression' → expresión SQL arbitraria.

        Returns:
            DataFrame transformado.
        """

    @abstractmethod
    def filter_columns(
        self, df: DataFrame, exclude_like=None, exclude_exact=None
    ) -> DataFrame:
        """Filtra columnas de un DataFrame, excluyendo por patrón o coincidencia exacta.

        No es case-sensitive.
        """

    @abstractmethod
    def ensure_columns(self, df: DataFrame, columns: List[str]) -> DataFrame:
        """Asegura que el DataFrame tenga todas las columnas indicadas.

        Agrega las columnas faltantes como NULL y devuelve el DataFrame
        con las columnas en el orden especificado.
        """

    @abstractmethod
    def sort_rows(
        self, df: DataFrame, columns: List[str], ascending: Optional[List[bool]] = None
    ) -> DataFrame:
        """Ordena las filas por columnas específicas.

        Args:
            df: DataFrame de entrada.
            columns: Columnas por las cuales ordenar.
            ascending: Lista de booleanos (True = ASC). Por defecto todas ASC.

        Returns:
            DataFrame ordenado.
        """

    @abstractmethod
    def merge_upsert(
        self,
        source_df: DataFrame,
        target_table_path: str,
        merge_keys: List[str],
        update_columns: Optional[Dict[str, str]] = None,
        insert_columns: Optional[Dict[str, str]] = None,
    ) -> None:
        """Realiza un MERGE (upsert) contra una tabla Delta.

        Args:
            source_df: DataFrame con los datos nuevos/actualizados.
            target_table_path: Ruta completa de la tabla Delta destino.
            merge_keys: Columnas que identifican de manera única un registro.
            update_columns: {col_destino: col_fuente} a actualizar. None → todas.
            insert_columns: {col_destino: col_fuente} a insertar. None → todas.
        """

    @abstractmethod
    def execute_query(self, query: str) -> DataFrame:
        """Ejecuta una consulta SQL arbitraria.

        Args:
            query: Sentencia SQL a ejecutar.

        Returns:
            DataFrame con el resultado.
        """
