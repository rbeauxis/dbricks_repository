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

def discover_landing_volumes():
    """
    Explora la jerarquía de Unity Catalog para encontrar Volúmenes reales.
    La API de Files no permite navegar por carpetas virtuales (/Volumes/main),
    se requiere la API de Unity Catalog.
    """
    w = WorkspaceClient()
    print("\n--- Descubriendo Volúmenes en Unity Catalog (Zonas de Landing) ---")
    try:
        # Iterar sobre los catálogos a los que el usuario tiene acceso
        for catalog in w.catalogs.list():
            try:
                for schema in w.schemas.list(catalog_name=catalog.name):
                    # Ignoramos el information_schema por limpieza
                    if schema.name == 'information_schema': 
                        continue
                    try:
                        for volume in w.volumes.list(catalog_name=catalog.name, schema_name=schema.name):
                            vol_path = f"/Volumes/{catalog.name}/{schema.name}/{volume.name}"
                            vol_type = str(volume.volume_type).replace("VolumeType.", "")
                            print(f"[VOLUME] {vol_path} (Tipo: {vol_type})")
                    except Exception:
                        pass # Ignorar esquemas sin permisos de listar volúmenes
            except Exception:
                pass # Ignorar catálogos sin permisos de listar esquemas
    except Exception as e:
        print(f"Error al acceder a Unity Catalog: {e}")

def list_volume_path(path: str):
    """
    Lista el contenido de un Volumen de Unity Catalog usando la API correcta (w.files).
    """
    w = WorkspaceClient()
    print(f"--- Listando ruta Volume: {path} ---")
    try:
        # En el Databricks SDK, w.files maneja las rutas de Unity Catalog Volumes (/Volumes/...)
        for file_info in w.files.list_directory_contents(path):
            size_kb = file_info.file_size / 1024 if file_info.file_size else 0
            is_dir = "DIR " if file_info.is_directory else "FILE"
            print(f"[{is_dir}] {file_info.path} ({size_kb:.2f} KB)")
    except Exception as e:
        print(f"Error al listar volumen {path}: {e}")


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
    # ---------------------------------------------------------
    # 1. ZONAS DE LECTURA PÚBLICAS (Solo Lectura)
    # ---------------------------------------------------------
    print("\n[ZONAS PÚBLICAS]")
    # list_dbfs_path("/")
    # list_dbfs_path("/FileStore") # Bloqueado en muchos Workspaces Enterprise
    # list_dbfs_path("/databricks-datasets")
    
    # ---------------------------------------------------------
    # 2. ZONAS DE LANDING (Lectura / Escritura)
    # ---------------------------------------------------------
    print("\n[ZONAS DE LANDING Y ESCRITURA]")
    
    # A) Unity Catalog Volumes (El estándar moderno recomendado por Databricks)
    # En lugar de adivinar las rutas estáticas, escaneamos la cuenta:
    discover_landing_volumes()
    
    # Si encuentras un volumen en el paso anterior, descomenta esto para ver qué tiene adentro:
    # list_volume_path("/Volumes/tu_catalogo/tu_esquema/tu_volumen")
    
    # B) Workspace Files (Archivos de tu usuario)
    # Nota: El API de DBFS del SDK a veces puede mapear /Workspace/Users/
    # pero es más seguro acceder con el cliente `w.workspace` para Workspace Files.
    try:
        w = WorkspaceClient()
        mi_usuario = w.current_user.me().user_name
        print(f"\n--- Tu ruta personal segura en el Workspace: /Workspace/Users/{mi_usuario} ---")
        # Workspace Files es ideal para scripts y pequeños archivos de configuración.
    except Exception as e:
        pass

    # ---------------------------------------------------------
    # 3. EJEMPLO DE LECTURA SPARK
    # ---------------------------------------------------------
    # read_dbfs_file_spark("/databricks-datasets/flights/departuredelays.csv", format="csv")
    
    # Ejemplo de escritura/landing con Spark hacia un Volumen de Unity Catalog:
    # df.write.format("delta").mode("overwrite").save("dbfs:/Volumes/main/default/landing/mis_datos")
