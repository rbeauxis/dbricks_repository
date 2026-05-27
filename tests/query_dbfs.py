import os
from databricks.sdk import WorkspaceClient
from databricks.connect import DatabricksSession

def list_dbfs_path(path: str = "/"):
    """
    Lista los contenidos de una ruta en DBFS usando Databricks SDK.
    """
    # El WorkspaceClient toma automáticamente las credenciales 
    # de las variables de entorno (DATABRICKS_HOST, DATABRICKS_TOKEN)
    w = WorkspaceClient()
    
    print(f"--- Listando ruta DBFS: {path} ---")
    try:
        for file_info in w.dbfs.list(path):
            size_kb = file_info.file_size / 1024 if file_info.file_size else 0
            is_dir = "DIR " if file_info.is_dir else "FILE"
            print(f"[{is_dir}] {file_info.path} ({size_kb:.2f} KB)")
    except Exception as e:
        print(f"Error al listar {path}: {e}")


def read_dbfs_file_spark(path: str, format: str = "csv"):
    """
    Lee un archivo de datos desde DBFS usando Databricks Connect (Spark).
    """
    spark = DatabricksSession.builder.getOrCreate()
    print(f"\n--- Leyendo archivo con Spark: {path} ---")
    
    # Asegurar el prefijo dbfs:
    full_path = f"dbfs:{path}" if not path.startswith("dbfs:") else path
    
    try:
        df = spark.read.format(format).option("header", "true").option("inferSchema", "true").load(full_path)
        print(f"Esquema de {full_path}:")
        df.printSchema()
        print("Primeras 5 filas:")
        df.show(5)
    except Exception as e:
        print(f"Error al leer con Spark {path}: {e}")


if __name__ == "__main__":
    # 1. Exploración de carpetas usando el SDK
    # list_dbfs_path("/")
    # list_dbfs_path("/FileStore")
    list_dbfs_path("/databricks-datasets//online_retail")
    
    # 2. Ejemplo de cómo consultar datos usando Spark (Databricks Connect)
    # Descomenta y ajusta la ruta para leer un archivo real
    # read_dbfs_file_spark("/databricks-datasets/flights/departuredelays.csv", format="csv")
