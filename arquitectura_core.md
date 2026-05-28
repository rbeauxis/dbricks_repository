# Arquitectura del Core Framework — Databricks (PySpark + Delta Lake)

Este documento describe la arquitectura del framework de procesamiento de datos (`src/core`) adaptado para funcionar de forma nativa en Azure Databricks con PySpark y Delta Lake.

---

## 1. Visión General

El `core` es una librería interna de Python que implementa un framework ETL reutilizable. Provee:

- **Gestión de nombres** de tablas con Unity Catalog
- **Arquitectura Medallón** de 4 capas: Landing (Externa/Workspace), RAW (Bronze), CURATED (Silver), CONSUMPTION (Gold)
- **Operaciones de datos** desacopladas del motor (PySpark / Delta Lake)
- **Un framework de 12 pasos** (`BaseProcessing`) para estandarizar pipelines ETL
- **Integración con Google Drive** para carga de archivos Excel / CSV
- **Gestión de secretos** compatible con entorno local y Databricks

La `SparkSession` **nunca se instancia en el core**. La provee el runtime de Databricks (notebook, job, o databricks-connect local) y se pasa como parámetro a cada componente.

---

## 2. Estructura del Directorio

```
src/
├── init/                                # Scripts SQL (DDL) para creación de infraestructura (Esquemas, Unity Catalog)
│   └── 00_init_dw_environment.sql       # Inicialización de capas gobernadas
├── core/
│   ├── __init__.py                      # Exportaciones públicas del paquete
├── secrets.py                           # Gestión de secretos (dbutils / .env)
│
├── db/
│   ├── __init__.py
│   ├── manager.py                       # Unity Catalog: catalog.schema.table
│   └── operations/
│       ├── __init__.py
│       ├── interface.py                 # Contrato abstracto de operaciones
│       ├── databricks.py                # Implementación PySpark + Delta Lake
│       └── factory.py                   # Factory de operaciones
│
├── apis/
│   └── gdrive/
│       ├── __init__.py
│       ├── gdrive_auth.py               # Autenticación OAuth con Google Drive
│       ├── gdrive_files.py              # Descarga de archivos desde Drive
│       └── gdrive_folders.py            # Listado de carpetas en Drive
│
└── proc/
    ├── datetime_transformer.py          # Transformaciones de fecha/hora
    └── base/
        ├── table.py                     # Representación de tabla de datos
        ├── processing.py                # Framework ETL de 12 pasos (BaseProcessing)
        └── load_files_gdrive.py         # Carga de Excel / CSV desde Google Drive
```

---

## 3. Componente: Secretos (`secrets.py`)

Abstrae el acceso a secretos según el entorno de ejecución:

| Entorno | Mecanismo |
|---|---|
| **Local** (`ENTORNO_LOCAL=true`) | Lee del archivo `.env` vía `python-dotenv` |
| **Databricks** | `dbutils.secrets.get(scope, key)` |

```python
from core.secrets import get_secret

api_key = get_secret("GDRIVE_API_KEY")
```

El scope de secretos se configura con la variable de entorno `DATABRICKS_SECRET_SCOPE` (default: `"default"`).

---

## 4. Componente: DatabaseManager (`db/manager.py`)

Construye rutas de tabla de 3 niveles siguiendo el estándar de Unity Catalog:

```
catalog . schema_ambiente . tabla
```

El catálogo por defecto utilizado como estándar en Unity Catalog es `main`.

### Capas de la Arquitectura Medallón

La plataforma adopta la arquitectura medallón con 4 capas lógicas:

1. **Landing (Zona de Aterrizaje)**: **Externa** al catálogo gestionado (Unity Catalog). Los archivos físicos (CSV, JSON) se depositan en el Workspace (`LANDING_URL`) o en un Data Lake externo. No utiliza un esquema de DB gestionado.
2. **RAW (Bronze)**: Primera capa gestionada de Unity Catalog. Contiene Tablas Delta administradas (Managed Tables) con los datos crudos ingestados desde Landing.
3. **CURATED (Silver)**: Tablas gestionadas con datos limpios, estandarizados y combinados.
4. **CONSUMPTION (Gold)**: Tablas gestionadas orientadas al usuario final (modelos dimensionales en estrella, agregaciones listas para BI).

### Ambientes disponibles en el Framework

| `Environment` | Valor del esquema |
|---|---|
| `RAW` | `raw` |
| `CURATED` | `curated` |
| `CONSUMPTION` | `consumption` |

### Aislamiento por usuario en desarrollo

Cuando `ENTORNO_LOCAL=true`, el nombre del esquema se prefija con el nombre del usuario (leído de `DATABRICKS_DEV_USER`) para aislar los datos de prueba de cada desarrollador y evitar colisiones:

| Entorno | Ejemplo de ruta completa |
|---|---|
| Producción | `workspace.curated.dt_tipo_documento` |
| Desarrollo (user: rbeauxisconsultor) | `workspace.rbeauxisconsultor_curated.dt_tipo_documento` |

```python
from core.db.manager import DatabaseManager, Environment

db = DatabaseManager(env=Environment.CURATED, table="dt_tipo_documento")
ruta = db.get_table_path()
# Producción:   "workspace.curated.dt_tipo_documento"
# Desarrollo:   "workspace.rbeauxisconsultor_curated.dt_tipo_documento"
```

---

## 5. Componente: Operaciones de Datos

### Arquitectura en capas

```
DataOperationsInterface (interface.py)   ← Contrato abstracto
        ↑
DatabricksOperations (databricks.py)     ← Implementación PySpark + Delta Lake
        ↑
DataOperationsFactory (factory.py)       ← Punto de entrada
```

### Uso

```python
from core import DataOperationsFactory

data_ops = DataOperationsFactory.create(spark)   # spark = sesión del runtime
df = data_ops.table_input("workspace.curated.dt_tipo_documento")
```

### Operaciones disponibles

| Método | Descripción |
|---|---|
| `table_input(table, columns, filters)` | Lee una tabla Delta |
| `table_output(df, table_path, mode)` | Escribe en una tabla Delta (`overwrite`, `append`, etc.) |
| `merge_upsert(source_df, target_path, keys)` | MERGE nativo de Delta Lake |
| `delete_from_table(source, target, keys)` | Borrado por MERGE Delta |
| `filter_rows(df, condition)` | Filtro SQL sobre DataFrame |
| `select_values(df, transformations)` | Proyección y renombrado via `selectExpr` |
| `filter_columns(df, exclude_like, exclude_exact)` | Exclusión de columnas por patrón |
| `ensure_columns(df, columns)` | Agrega columnas faltantes como NULL |
| `sort_rows(df, columns, ascending)` | Ordenamiento |
| `execute_query(sql)` | Ejecución SQL arbitraria |

---

## 6. Componente: Framework ETL de 12 Pasos (`BaseProcessing`)

El corazón del framework. Define un flujo ETL estandarizado que toda clase de procesamiento de negocio debe extender.

### Diagrama de flujo

```
BaseProcessing.run()
│
├─ [00] _00_get_tables()              → Fuentes adicionales (dinámicas)
├─ [01] _01_read_source(sources)      → Lectura de todas las fuentes
├─ [02] _02_pre_filter(dict_dfs)      → Filtros previos al join
├─ [03] _03_join(dict_dfs)            → Join entre fuentes
├─ [04] _04_transform(df)             → ⭐ Transformación principal (negocio)
├─ [05] _05_add_default_row(df)       → Fila por defecto (ej. dimensión nula)
├─ [06] _06_add_modification_timestamp(df)  → Columna fecha_modif
├─ [07] _07_add_default_column(df)    → Columnas adicionales por defecto
│
├─ [08] _08_is_only_insert()          → ¿Solo inserción? (True/False)
│        ├── False → [09] _09_upsert(df)        → MERGE Delta Lake
│        └── True  → [10] _10_table_output(df)  → Escritura directa
│
└─ [11] _11_post_save_process(dest)   → Post-procesamiento (notificaciones, limpieza)
```

### Implementación mínima de una clase hija

```python
from pyspark.sql import DataFrame
from core.proc.base.processing import BaseProcessing
from core.proc.base.table import Table
from core.db.manager import Environment

class ProcesarDimensionEjemplo(BaseProcessing):

    def _04_transform(self, joined_df: DataFrame) -> DataFrame:
        return joined_df.withColumnRenamed("id_origen", "id_dimension")

    def upsert_merge_keys(self):
        return ["id_dimension"]


# Uso en un job de Databricks:
source = Table(table="origen_raw", env=Environment.RAW)
dest   = Table(table="dim_ejemplo", env=Environment.CURATED)

proc = ProcesarDimensionEjemplo(session=spark, destination=dest, sources=[source])
proc.run()
```

### Puntos de extensión por defecto

| Método | Comportamiento por defecto | Sobrescribir cuando... |
|---|---|---|
| `_00_get_tables()` | `{}` (vacío) | Necesitas fuentes adicionales dinámicas |
| `_02_pre_filter()` | Sin filtros | Necesitas filtrar antes del join |
| `_03_join()` | Retorna la primera fuente | Tienes múltiples fuentes que combinar |
| `_04_transform()` | Sin transformación | **Siempre** — es la lógica de negocio |
| `_05_add_default_row()` | DataFrame vacío (schema igual) | Quieres definir una fila null específica |
| `_07_add_default_column()` | Sin columnas extra | Necesitas columnas de auditoría adicionales |
| `_08_is_only_insert()` | `False` (hace upsert) | La tabla es de solo inserción (hechos) |
| `upsert_merge_keys()` | `[]` | **Siempre** si usas upsert |
| `table_output_mode()` | `"append"` | Quieres `"overwrite"` |
| `_11_post_save_process()` | No-op | Necesitas lógica post-guardado |

---

## 7. Componente: Tabla (`Table`)

Representa una tabla de datos con su ambiente, nombre y configuración de lectura.

```python
from core.proc.base.table import Table
from core.db.manager import Environment

tabla = Table(
    table="fact_ventas",
    env=Environment.CURATED,
    columns=["id_venta", "monto", "fecha"],      # opcional: proyección
    rename_map={"id_venta": "venta_id"},          # opcional: renombrado
    cache_result=True,                            # opcional: cachear en Spark
)

df = tabla.read_source(data_ops=data_ops)
ruta = tabla.get_table_path()   # → "workspace.curated.fact_ventas"
```

---

## 8. Componente: Carga desde Google Drive

Para cargar archivos Excel o CSV directamente desde Google Drive a una tabla Delta.

```python
from core.proc.base.load_files_gdrive import LoadGdriveExcelToDatabricks
from core.proc.base.table import Table
from core.db.manager import Environment

dest = Table(table="presupuesto_raw", env=Environment.RAW)

loader = LoadGdriveExcelToDatabricks(
    session=spark,
    destination=dest,
    source_id="1ABC_ID_DEL_ARCHIVO_EN_DRIVE",
    sheet_name="Hoja1",
    ignore_unnamed=True,
)
loader.run()  # Descarga → Limpia → Guarda en Delta
```

---

## 9. Gestión de la SparkSession

> [!IMPORTANT]
> El `core` **nunca crea ni gestiona la SparkSession**. Siempre se pasa como parámetro.

| Contexto | Cómo obtener `spark` |
|---|---|
| **Notebook Databricks** | Variable global `spark` inyectada por el runtime |
| **Job Databricks** | Variable global `spark` inyectada por el runtime |
| **Local (databricks-connect)** | `DatabricksSession.builder.getOrCreate()` (gestionado por `tests/conftest.py`) |

Esto elimina cualquier singleton de conexión innecesario y delega la responsabilidad al runtime, que es quien la conoce mejor.

---

## 10. Variables de Entorno

| Variable | Uso | Ejemplo |
|---|---|---|
| `ENTORNO_LOCAL` | Activa el modo local (`.env`, esquemas por usuario) | `true` |
| `DATABRICKS_DEV_USER` | Usuario para aislar esquemas en desarrollo | `rbeauxisconsultor@gmail.com` |
| `DATABRICKS_SECRET_SCOPE` | Scope de secretos en Databricks | `default` |
| `DATABASE_PREFIX` | Prefijo alternativo para el esquema (local) | `BI_T` |
