from typing import List, Optional, Union

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.functions import col, lit, to_timestamp, trim, when


class DateTransformer:
    """Utilidades para transformar columnas de fecha/hora en DataFrames de PySpark."""

    def agregar_columnas_sk(
        self,
        df: DataFrame,
        timestamp_col: Union[str, List[str]] = "log_timestamp",
        col_fecha: Union[str, List[str]] = "sk_fecha",
        col_hora: Union[str, List[str]] = "sk_hora",
        drop_timestamp: Optional[bool] = True,
    ) -> DataFrame:
        """
        Agrega columnas con claves surrogate de fecha y hora a partir de uno o
        múltiples timestamps.

        Args:
            df: DataFrame de entrada.
            timestamp_col: Nombre(s) de la(s) columna(s) de timestamp original(es).
            col_fecha: Nombre(s) de la(s) nueva(s) columna(s) para sk_fecha (YYYYMMDD).
            col_hora: Nombre(s) de la(s) nueva(s) columna(s) para sk_hora (HHmm).
            drop_timestamp: Si True, elimina la(s) columna(s) de timestamp original(es).

        Returns:
            DataFrame con las columnas nuevas agregadas.

        Examples:
            # Un solo timestamp
            df_result = transformer.agregar_columnas_sk(
                df, timestamp_col="created_at", col_fecha="sk_fecha", col_hora="sk_hora"
            )

            # Múltiples timestamps
            df_result = transformer.agregar_columnas_sk(
                df,
                timestamp_col=["created_at", "updated_at"],
                col_fecha=["sk_fecha_created", "sk_fecha_updated"],
                col_hora=["sk_hora_created", "sk_hora_updated"],
            )
        """
        if isinstance(timestamp_col, str):
            timestamp_col = [timestamp_col]
        if isinstance(col_fecha, str):
            col_fecha = [col_fecha]
        if isinstance(col_hora, str):
            col_hora = [col_hora]

        if not (len(timestamp_col) == len(col_fecha) == len(col_hora)):
            raise ValueError(
                f"Todas las listas deben tener la misma longitud. "
                f"timestamp_col: {len(timestamp_col)}, "
                f"col_fecha: {len(col_fecha)}, "
                f"col_hora: {len(col_hora)}"
            )

        result_df = df
        for ts_col, fecha_col, hora_col in zip(timestamp_col, col_fecha, col_hora):
            result_df = (
                result_df
                .withColumn(fecha_col, F.date_format(F.col(ts_col), "yyyyMMdd").cast("int"))
                .withColumn(hora_col, F.date_format(F.col(ts_col), "HHmm").cast("int"))
            )

        if drop_timestamp:
            result_df = result_df.drop(*timestamp_col)

        return result_df

    def sanitize_timestamp_columns(
        self,
        df: DataFrame,
        columns: List[str],
        default: str = "1900-01-01 00:00:00",
    ) -> DataFrame:
        """
        Convierte columnas STRING a TIMESTAMP. Si el valor es inválido, nulo
        o vacío, lo reemplaza por un timestamp fijo (por defecto '1900-01-01 00:00:00').

        Args:
            df: DataFrame original.
            columns: Lista de columnas a convertir.
            default: Valor por defecto si no se puede convertir.

        Returns:
            DataFrame con las columnas transformadas.
        """
        for c in columns:
            df = df.withColumn(
                c,
                when(
                    trim(col(c)).rlike(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"),
                    to_timestamp(trim(col(c)), "yyyy-MM-dd HH:mm:ss"),
                ).otherwise(lit(default).cast("timestamp")),
            )
        return df
