import os
from dotenv import load_dotenv
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import ResourceDoesNotExist

# Cargar variables del .env
load_dotenv()

def create_landing_zone():
    """
    Lee la variable LANDING_URL del entorno y si apunta a una ruta local
    del Workspace (/Workspace/Users/...), intenta crear el directorio.
    """
    landing_url = os.environ.get("LANDING_URL")
    
    if not landing_url:
        print("❌ Error: La variable LANDING_URL no está definida en el archivo .env")
        return

    print(f"🔍 Evaluando zona de Landing configurada: {landing_url}")

    # Si es una ruta interna del Databricks Workspace
    if landing_url.startswith("/Workspace/"):
        w = WorkspaceClient()
        try:
            # Comprueba si el directorio ya existe
            w.workspace.get_status(landing_url)
            print("✅ El directorio de Landing ya existe. No es necesario crearlo.")
        except ResourceDoesNotExist:
            # Si no existe, lo creamos
            print("🔨 El directorio no existe. Creándolo en el Workspace...")
            w.workspace.mkdirs(landing_url)
            print("✅ ¡Directorio de Landing creado con éxito!")
        except Exception as e:
            print(f"❌ Error inesperado al interactuar con el Workspace: {e}")
            
    # Si es una ruta externa de Cloud (Ej. ADLS Gen2 o S3)
    elif landing_url.startswith("abfss://") or landing_url.startswith("s3://"):
        print("☁️ La ruta configurada es un Data Lake externo en la nube.")
        print("Este tipo de directorios debe ser aprovisionado por el equipo de Infraestructura (Ej. usando Terraform).")
        
    else:
        print("⚠️ Ruta no reconocida. Asegúrate de usar /Workspace/... o abfss://...")

if __name__ == "__main__":
    print("-" * 50)
    print("Inicializador de Zona de Aterrizaje (Landing Zone)")
    print("-" * 50)
    create_landing_zone()
