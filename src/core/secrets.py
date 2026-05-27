"""
Gestión de secretos para Databricks.

- En entorno local (ENTORNO_LOCAL=true): lee del archivo .env vía python-dotenv.
- En Databricks: obtiene secretos usando DBUtils(spark) — el estándar oficial.
"""
import os
from typing import Optional

IS_LOCAL = os.getenv("ENTORNO_LOCAL", "False").lower() == "true"

if IS_LOCAL:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _get_dbutils():
    """
    Obtiene dbutils usando el método oficial de Databricks para código de librería.

    Fuera de notebooks (jobs, scripts, tests), dbutils no está en el scope global.
    El estándar es instanciarlo a través de la SparkSession activa con DBUtils(spark).

    Ref: https://docs.databricks.com/en/dev-tools/databricks-utils.html#dbutils-in-python
    """
    try:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.getActiveSession()
        if spark is not None:
            return DBUtils(spark)
    except Exception:
        pass
    return None


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Obtiene un secreto por clave.

    En entorno local lo lee de las variables de entorno (.env).
    En Databricks lo obtiene desde dbutils.secrets (scope configurado con
    la variable de entorno DATABRICKS_SECRET_SCOPE, default: "default").
    """
    if IS_LOCAL:
        return os.getenv(key, default)

    dbutils = _get_dbutils()
    if dbutils is not None:
        scope = os.getenv("DATABRICKS_SECRET_SCOPE", "default")
        try:
            return dbutils.secrets.get(scope=scope, key=key)
        except Exception:
            if default is not None:
                return default
            raise

    raise RuntimeError(
        "No se pudo obtener el secreto: dbutils no disponible y no es entorno local. "
        "Asegúrate de que haya una SparkSession activa (el código debe correr en Databricks)."
    )


def get_secret_db_prefix() -> str:
    """Obtiene el prefijo del esquema de la base de datos según entorno."""
    return get_secret("DATABASE_PREFIX", "BI_T")


def get_entorno_local() -> bool:
    """Retorna True si la aplicación corre en entorno local."""
    return IS_LOCAL
