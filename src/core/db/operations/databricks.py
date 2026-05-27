"""
Implementación concreta de DataOperationsInterface para Databricks (PySpark + Delta Lake).
"""
from typing import Dict, List, Optional, Union

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from core.db.operations.interface import DataOperationsInterface


class DatabricksOperations(DataOperationsInterface):
    """
    Operaciones de datos para Databricks usando PySpark y Delta Lake.

    Attributes:
        session: SparkSession activa.
    """

    def __init__(self, session: SparkSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def table_input(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Union[str, int, float, bool]]] = None,
    ) -> DataFrame:
        """Lee datos de una tabla Delta en Unity Catalog.

        Args:
            table_name: Nombre completo (catalog.schema.table).
            columns: Columnas a seleccionar. None → todas.
            filters: Filtros simples de igualdad {columna: valor}.

        Returns:
            DataFrame de PySpark.
        """
        df = self.session.table(table_name)

        if filters:
            for column, value in filters.items():
                df = df.filter(F.col(column) == value)

        if columns:
            df = df.select(*columns)

        return df

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

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
            mode: 'overwrite' | 'append' | 'ignore' | 'errorifexists'.
        """
        allowed_modes = {"overwrite", "append", "ignore", "errorifexists"}
        if mode not in allowed_modes:
            raise ValueError(f"Modo '{mode}' no válido. Debe ser uno de: {allowed_modes}")
        df.write.format("delta").mode(mode).saveAsTable(table_path)

    # ------------------------------------------------------------------
    # Merge / Upsert (Delta Lake nativo)
    # ------------------------------------------------------------------

    def merge_upsert(
        self,
        source_df: DataFrame,
        target_table_path: str,
        merge_keys: List[str],
        update_columns: Optional[Dict[str, str]] = None,
        insert_columns: Optional[Dict[str, str]] = None,
    ) -> None:
        """Realiza un MERGE optimizado usando la API de Delta Lake.

        Args:
            source_df: DataFrame con los datos nuevos/actualizados.
            target_table_path: Ruta completa de la tabla Delta destino.
            merge_keys: Columnas que identifican de manera única un registro.
            update_columns: {col_destino: col_fuente} a actualizar. None → todas.
            insert_columns: {col_destino: col_fuente} a insertar. None → todas.
        """
        delta_target = DeltaTable.forName(self.session, target_table_path)

        # Construir la condición de join a partir de las claves de merge
        merge_condition = " AND ".join(
            [f"target.{k} = source.{k}" for k in merge_keys]
        )

        all_cols = source_df.columns

        update_set = update_columns if update_columns else {c: f"source.{c}" for c in all_cols}
        insert_set = insert_columns if insert_columns else {c: f"source.{c}" for c in all_cols}

        (
            delta_target.alias("target")
            .merge(source_df.alias("source"), merge_condition)
            .whenMatchedUpdate(set=update_set)
            .whenNotMatchedInsert(values=insert_set)
            .execute()
        )

    # ------------------------------------------------------------------
    # Borrado de registros
    # ------------------------------------------------------------------

    def delete_from_table(
        self,
        source_path: str,
        table_path: str,
        key_columns: Dict[str, str],
    ) -> None:
        """Borra registros de la tabla Delta usando un MERGE con fuente de deletes.

        Args:
            source_path: Vista/tabla que contiene los registros a eliminar.
            table_path: Tabla Delta destino.
            key_columns: {columna_destino: columna_fuente} para el join.
        """
        join_conditions = " AND ".join(
            [f"target.{t} = source.{s}" for t, s in key_columns.items()]
        )
        self.session.sql(f"""
            MERGE INTO {table_path} AS target
            USING {source_path} AS source
            ON {join_conditions}
            WHEN MATCHED THEN DELETE
        """)

    # ------------------------------------------------------------------
    # Filtros y transformaciones
    # ------------------------------------------------------------------

    def filter_rows(self, df: DataFrame, condition: str) -> DataFrame:
        """Filtra filas según una condición SQL."""
        return df.filter(condition)

    def select_values(
        self, df: DataFrame, transformations: Dict[str, Union[str, Dict[str, str]]]
    ) -> DataFrame:
        """Selecciona y transforma columnas usando selectExpr."""
        expressions = []
        for new_name, transform in transformations.items():
            if isinstance(transform, str):
                expressions.append(f"{transform} AS {new_name}")
            elif isinstance(transform, dict):
                expressions.append(f"{transform['expression']} AS {new_name}")
        return df.selectExpr(*expressions)

    def filter_columns(
        self, df: DataFrame, exclude_like=None, exclude_exact=None
    ) -> DataFrame:
        """Filtra columnas excluyendo por patrón o coincidencia exacta (no case-sensitive)."""
        exclude_like = exclude_like or []
        exclude_exact = exclude_exact or []
        cols = [
            c for c in df.columns
            if all(like.lower() not in c.lower() for like in exclude_like)
            and c.lower() not in [e.lower() for e in exclude_exact]
        ]
        return df.select(*cols)

    def ensure_columns(self, df: DataFrame, columns: List[str]) -> DataFrame:
        """Asegura que el DataFrame tenga todas las columnas, agregando las faltantes como NULL."""
        for col in columns:
            if col not in df.columns:
                df = df.withColumn(col, F.lit(None))
        return df.select(*columns)

    def sort_rows(
        self, df: DataFrame, columns: List[str], ascending: Optional[List[bool]] = None
    ) -> DataFrame:
        """Ordena las filas por columnas específicas."""
        if ascending is None:
            ascending = [True] * len(columns)
        order_exprs = [
            F.col(c).asc() if asc else F.col(c).desc()
            for c, asc in zip(columns, ascending)
        ]
        return df.orderBy(*order_exprs)

    # ------------------------------------------------------------------
    # SQL
    # ------------------------------------------------------------------

    def execute_query(self, query: str) -> DataFrame:
        """Ejecuta una consulta SQL arbitraria."""
        return self.session.sql(query)
