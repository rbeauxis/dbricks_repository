from __future__ import annotations

import io
import logging
import re
import unicodedata
from functools import reduce
from typing import Optional

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from core import DataOperationsFactory
from core.apis.gdrive.gdrive_files import get_file_content
from core.proc.base.table import Table

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LoadGdriveExcelToDatabricks:
    """
    Carga un archivo Excel desde Google Drive y lo persiste en una tabla Delta.

    Pasos:
        1. Descarga el archivo desde Google Drive.
        2. Limpia y normaliza el DataFrame de Pandas.
        3. Convierte y guarda en la tabla Delta de destino.
    """

    def __init__(
        self,
        session: SparkSession,
        destination: Table,
        source_id: str,
        sheet_name: Optional[str] = None,
        skiprows: Optional[int] = None,
        encoding: Optional[str] = "utf-8",
        ignore_unnamed: Optional[bool] = False,
    ) -> None:
        """
        Args:
            session: SparkSession activa de Databricks.
            destination: Tabla Delta destino.
            source_id: ID del archivo en Google Drive.
            sheet_name: Nombre de la hoja a leer (Excel). None → primera hoja.
            skiprows: Número de filas a saltar al inicio.
            encoding: Codificación del archivo.
            ignore_unnamed: Si True, elimina columnas con nombre 'UNNAMED_N'.
        """
        self.session = session
        self.data_ops = DataOperationsFactory.create(session)
        self.source_id = source_id
        self.destination = destination
        self.sheet_name = sheet_name
        self.skiprows = skiprows
        self.encoding = encoding
        self.ignore_unnamed = ignore_unnamed

    def run(self) -> None:
        """Ejecuta el flujo completo: descarga → limpieza → guardado."""
        source_df = self._01_read_source(self.source_id)
        transformed_df = self._02_clean(source_df)
        self._03_save_data(transformed_df)

    # ------------------------------------------------------------------
    # Pasos internos
    # ------------------------------------------------------------------

    def _01_read_source(self, source_id: str) -> pd.DataFrame:
        """Descarga y lee el archivo Excel desde Google Drive."""
        file_content = get_file_content(file_id=source_id)
        if not file_content:
            raise Exception(
                f"Failed to download file content from Google Drive. File ID: {source_id}"
            )

        params: dict = {"io": io.BytesIO(file_content)}
        if self.sheet_name:
            params["sheet_name"] = self.sheet_name
        if self.skiprows:
            params["skiprows"] = self.skiprows

        df = pd.read_excel(**params)
        if df.empty:
            raise Exception("Excel file is empty, no data to load.")
        return df

    def _02_clean(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza nombres de columnas y tipos de datos."""
        # Normalizar nombres de columnas: quitar acentos y caracteres especiales
        source_df.columns = [
            unicodedata.normalize("NFD", col).encode("ascii", "ignore").decode("ascii")
            for col in source_df.columns
        ]
        source_df.columns = [
            re.sub(r"_{2,}|_$", "_", re.sub(r"[^\w]", "_", col.strip())).rstrip("_").upper()
            for col in source_df.columns
        ]

        if self.ignore_unnamed:
            source_df = source_df.loc[
                :, ~source_df.columns.str.match(r"^UNNAMED_\d+$", case=False)
            ]

        df = source_df.convert_dtypes()

        # Convertir columnas object a string
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str)

        # Convertir columnas de fecha
        for col in df.columns:
            if "FECHA" in col.upper() or "DATE" in col.upper():
                try:
                    temp_series = pd.to_datetime(df[col], errors="coerce")
                    df[col] = temp_series.where(temp_series.notna(), pd.NA)
                    logger.info(f"Columna '{col}' - Valores nulos: {df[col].isna().sum()}")
                except Exception as e:
                    logger.warning(f"Error convirtiendo columna {col}: {e}")
                    df[col] = df[col].astype(str)

        return df

    def _03_save_data(self, transformed_df: pd.DataFrame) -> None:
        """Convierte el DataFrame de Pandas a Spark y lo guarda en la tabla Delta."""
        # Convertir Timestamps a string ISO para evitar problemas de serialización
        for col in transformed_df.columns:
            if transformed_df[col].dtype == "datetime64[ns]" or (
                not transformed_df[col].empty
                and isinstance(transformed_df[col].iloc[0], pd.Timestamp)
            ):
                logger.info(f"Convirtiendo Timestamp en columna: {col}")
                transformed_df[col] = transformed_df[col].apply(
                    lambda x: None if pd.isna(x) else str(x)
                )

        # Limpiar valores nulos representados como strings
        transformed_df = transformed_df.replace(
            {"<NA>": None, "NaT": None, "NaN": None, "nan": None, "nat": None}
        )

        # Asegurar nulos en columnas numéricas
        for col in transformed_df.columns:
            dtype_str = str(transformed_df[col].dtype)
            if any(t in dtype_str for t in ["int", "float", "Int", "Float"]):
                transformed_df[col] = pd.to_numeric(transformed_df[col], errors="coerce")
                transformed_df[col] = transformed_df[col].where(
                    pd.notna(transformed_df[col]), None
                )

        records = transformed_df.to_dict("records")
        spark_df = self.session.createDataFrame(records)

        # Filtrar filas completamente vacías
        non_null_exprs = [F.when(F.col(c).isNotNull(), 1).otherwise(0) for c in spark_df.columns]
        if non_null_exprs:
            total_expr = reduce(lambda x, y: x + y, non_null_exprs)
            spark_df = spark_df.withColumn("_non_null_count", total_expr)
            spark_df = spark_df.filter(F.col("_non_null_count") > 0)
            spark_df = spark_df.drop("_non_null_count")

        self.data_ops.table_output(
            df=spark_df,
            table_path=self.destination.get_table_path(),
            mode="overwrite",
        )


class LoadGdriveCsvToDatabricks(LoadGdriveExcelToDatabricks):
    """
    Carga un archivo CSV desde Google Drive y lo persiste en una tabla Delta.

    Extiende LoadGdriveExcelToDatabricks sobreescribiendo solo la lectura.
    """

    def __init__(
        self,
        session: SparkSession,
        destination: Table,
        source_id: str,
        delimiter: Optional[str] = ",",
        encoding: Optional[str] = "utf-8",
    ) -> None:
        """
        Args:
            session: SparkSession activa de Databricks.
            destination: Tabla Delta destino.
            source_id: ID del archivo CSV en Google Drive.
            delimiter: Separador de columnas (default: ',').
            encoding: Codificación del archivo (default: 'utf-8').
        """
        self.session = session
        self.data_ops = DataOperationsFactory.create(session)
        self.source_id = source_id
        self.destination = destination
        self.delimiter = delimiter
        self.encoding = encoding
        self.sheet_name = None
        self.skiprows = None
        self.ignore_unnamed = False

    def _01_read_source(self, source_id: str) -> pd.DataFrame:
        """Descarga y lee el archivo CSV desde Google Drive."""
        file_content = get_file_content(file_id=source_id)
        if not file_content:
            raise Exception(
                f"Failed to download file content from Google Drive. File ID: {source_id}"
            )

        df = pd.read_csv(
            io.BytesIO(file_content),
            delimiter=self.delimiter,
            encoding=self.encoding,
        )
        if df.empty:
            raise Exception("CSV file is empty, no data to load.")
        return df
