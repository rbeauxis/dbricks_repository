# Rutina de Instalación — Databricks Certification (Professional Flow)

Esta guía documenta la configuración de una estación de trabajo profesional para el curso "Databricks Certified Data Engineer Associate". El flujo de trabajo sigue el estándar de la industria: **Local → GitHub → Databricks Repos**.

---

## Arquitectura del Entorno

```mermaid
graph LR
    A[Antigravity / VS Code] -- git push --> B[GitHub (rbeauxis/dbricks_repository)]
    B -- git pull --> C[Databricks Workspace (Repos)]
    C -- ejecuta --> D[DemoCluster]
```

*(Representación gráfica en texto plano)*
```text
[ VS Code Local ] ── git push ──> [ GitHub Repo ] ── git pull ──> [ Databricks Repos ] ── ejecuta ──> [ Cluster ]
```

---

## 1. Pre-requisitos (Estación Local)

| Herramienta     | Versión    | Instalación |
|-----------------|------------|-------------|
| Python          | 3.11.9 ⚠️  | `winget install Python.Python.3.11` (ver nota abajo) |
| Python          | 3.12.8     | [python.org](https://python.org) (sistema, NO usar para el venv) |
| Git             | (Actual)   | [git-scm.com](https://git-scm.com) |
| VS Code         | (Actual)   | [visualstudio.com](https://code.visualstudio.com) |
| Databricks CLI  | 0.298.0    | `winget install Databricks.DatabricksCLI` |

> **⚠️ IMPORTANTE — Python 3.11 es obligatorio para el venv:** El cluster usa **DBR 13.3**, que internamente corre Python 3.10. `databricks-connect==13.3.*` depende de `distutils`, módulo eliminado en Python 3.12. Usar Python 3.12 para el venv genera `ModuleNotFoundError: No module named 'distutils'` y `KeyError: 'spark'`.

---

## 2. Configuración del Repositorio Git

### Paso 1: Inicialización Local
Si estás empezando desde cero, clona el repositorio original y conéctalo a tu propio GitHub:

```powershell
# 1. Clonar el contenido base
git clone https://github.com/repository-url-here .

# 2. Conectar a tu propio repositorio
git remote set-url origin https://github.com/rbeauxis/dbricks_repository.git

# 3. Configurar .gitignore (fundamental para no subir venv/)
# (Ya creado en la raíz)
```

### Paso 2: Configuración del Entorno de Desarrollo (venv con Python 3.11)
El venv **debe** crearse con Python 3.11 para compatibilidad con DBR 13.3.

1. **Verificar que Python 3.11 está disponible:**
   ```powershell
   py -3.11 --version
   # Si falla: winget install Python.Python.3.11
   ```
2. **Crear el venv con Python 3.11:**
   ```powershell
   py -3.11 -m venv .venv311
   ```
3. **Instalar dependencias clave:**
   Instalamos el SDK de Databricks y el soporte para celdas interactivas de VS Code:
   ```powershell
   # SDK de conexión remota con el cluster
   .venv311\Scripts\pip install databricks-connect==13.3.*

   # Soporte para ejecutar celdas interactivas (Notebooks) en VS Code
   .venv311\Scripts\pip install ipykernel
   ```
   > **⚠️ IMPORTANTE:** No instales `pyspark` manualmente. `databricks-connect` ya incluye de forma interna la versión correcta de PySpark compatible con el cluster.
4. **Seleccionar el intérprete en VS Code:**
   - `Ctrl+Shift+P` → **"Python: Select Interpreter"** → elegir `.venv311` (o el intérprete de tu entorno local si no lo ves listado).
   - O en la extensión de Databricks: `Ctrl+Shift+P` → **"Databricks: Select Python Interpreter"** → apuntar a `.venv311\Scripts\python.exe`.

---

## 3. Integración con Databricks

### Paso 1: Configurar Autenticación (CLI)
Para que las herramientas de VS Code y el CLI hablen con Azure Databricks. Usaremos el nombre de perfil `"luis_beauxis"` para que sea consistente con tu configuración actual de Databricks Asset Bundles:

```powershell
databricks auth login --host https://adb-7405609127094080.0.azuredatabricks.net --profile luis_beauxis
```
> **💡 Nota sobre perfiles:** Puedes usar el nombre de perfil que prefieras (por ejemplo, `dev`), pero asegúrate de usar el mismo nombre cuando configures tus proyectos, la extensión de VS Code o tus targets en el archivo `databricks.yml`. En esta guía asumiremos que usas `"luis_beauxis"`.

### Paso 2: Conectar Databricks Repos a GitHub
1. Entra a la Web de Databricks.
2. Ve a **Workspace** → **Repos**.
3. Clic en **Add Repo**.
4. URL: `https://github.com/rbeauxis/dbricks_repository.git`
5. Esto creará una carpeta sincronizada que es un "espejo" de tu GitHub.

---

## 4. Ciclo de Desarrollo Diario (Professional Flow)

1. **Modificar local:** Editas tus notebooks en VS Code (archivos `.py` formateados como notebooks).
2. **Subir cambios a GitHub:**
   ```powershell
   git add .
   git commit -m "Descripción del cambio"
   git push
   ```
3. **Actualizar Databricks (Pull):**
   - En la UI de Databricks, entra al Repo.
   - Clic en el nombre de la rama (**`main`**) arriba a la izquierda.
   - Clic en el botón **Pull**.

---

## 5. Gestión de Ramas (Branches)

- **Crear rama local:** `git checkout -b feature/nombre-tarea`.
- **Publicar rama:** `git push -u origin feature/nombre-tarea`.
- **Cambiar rama en Databricks:** Desde el panel de Git (clic en la rama arriba a la izquierda), selecciona la nueva rama bajo "Remote branches".
- **Merge:** Se recomienda usar Pull Requests en GitHub y luego hacer `Pull` en Databricks sobre la rama `main`.


---

## 6. Databricks Asset Bundles (DAB) — Flujo de Infraestructura como Código

**Databricks Asset Bundles (DAB)** es el enfoque profesional y moderno para desarrollar, probar y desplegar proyectos complejos en Databricks. A diferencia del flujo tradicional de Repos Git interactivos:
- **Infraestructura como Código (IaC):** Permite definir tus workflows (Jobs), Delta Live Tables (Pipelines) y recursos asociados en archivos YAML (`databricks.yml`).
- **Aislamiento de Entornos:** Despliega tu código de forma automática en rutas de desarrollo individuales (por ejemplo, `/Users/usuario/.bundle/proyecto/dev`) para que puedas probar sin interferir con las carpetas compartidas ni el Repo de Git principal.
- **Ciclo Automatizado:**
  - **Validación:** `databricks bundle validate` comprueba que la configuración sea sintácticamente correcta.
  - **Despliegue rápido:** `databricks bundle deploy -t dev` compila y sube el proyecto a tu entorno personal de desarrollo.
  - **Desarrollo en tiempo real (Watch):**
    ```powershell
    databricks bundle sync -t dev --watch
    ```
    Este comando detecta cambios locales en tiempo real y los sincroniza instantáneamente con tu Workspace en una ruta de desarrollo segura, ideal para iteraciones rápidas sin chocar con Git.

> **⚠️ REGLA DE SEGURIDAD OBLIGATORIA (Especificar siempre el Target `-t`):** Aunque un target esté marcado como predeterminado (`default: true`), es una práctica de ingeniería obligatoria especificar siempre el flag `-t <entorno>` de forma explícita en todos tus comandos de deploy, run o sync (ej: `databricks bundle deploy -t dev` o `databricks bundle deploy -t prod`). Esto evita accidentes de sobreescritura involuntaria de recursos o entornos equivocados en el futuro.

---

## 7. Creación de un Proyecto desde Cero (Configuración en VS Code IDE)

Para inicializar un proyecto de Databricks Asset Bundles (DAB) completamente desde cero utilizando el IDE de VS Code, sigue esta guía estructurada paso a paso:

1. **Descargar extensión Databricks:** Búscala e instálala desde el Marketplace de extensiones en VS Code.
2. **CREATE A NEW DATABRICKS PROJECT:** Haz clic en el ícono de Databricks en la barra de actividad de VS Code y selecciona esta opción para iniciar el asistente de creación.
3. **Indicar la URL del Workspace:** Ingresa la URL de tu espacio de trabajo de Azure Databricks (por ejemplo, `https://adb-7405609127094080.0.azuredatabricks.net`).
4. **Autenticación OAUTH:** Selecciona OAuth (método recomendado y más seguro).
5. **Asignar nombre de perfil:** Escribe `"dev"` como el nombre del perfil.
6. **Autenticado:** Se abrirá una pestaña en el navegador para iniciar sesión. Tras autorizar el acceso, volverás a VS Code ya autenticado.
7. **Seleccionar ruta y crear directorio de proyecto:** Selecciona el directorio en tu máquina local donde deseas alojar el proyecto.
8. **Inicializar el Bundle (Asistente en la terminal):** Ejecuta el siguiente comando en tu terminal integrada de VS Code/Antigravity:
   ```powershell
   databricks bundle init
   ```
9. **Configuración de Plantilla Limpia ("Lienzo en Blanco"):** Para aprender y tener un control absoluto sobre tu código, te recomendamos rechazar todos los artefactos de ejemplo prefabricados respondiendo de la siguiente manera en la terminal:
   *   **Template to use (Plantilla a elegir):** Selecciona **`default-python`** (es la plantilla estándar oficial de Databricks para proyectos de ingeniería de datos, DLT y flujos CDC en Python y SQL).
   *   **Nombre de proyecto:** Ingresa el nombre (por ejemplo, `mi_proyecto_cdc`).
   *   **Include a notebook:** Selecciona **`no`** (para no generar código de ejemplo genérico).
   *   **Include a Delta Live Tables pipeline:** Selecciona **`no`** (para no generar archivos de prueba).
   *   **Include a Python package:** Selecciona **`no`** (para evitar carpetas complejas de empaquetado).
   *   **Include a job that runs a notebook:** Selecciona **`no`** (para no generar flujos/workflows genéricos prefabricados).
   *   **Use serverless compute:** Selecciona **`no`** (⚠️ **MANDATORIO EN COMMUNITY EDITION:** Databricks Community Edition no soporta cómputo serverless; elegir `yes` provocará fallos críticos de API al desplegar. Debes usar tu cluster gratuito tradicional).
   *   **Default catalog for any tables created by this project:** Presiona **`Enter`** para dejar el valor por defecto (`[workspace]`), asegurando la máxima compatibilidad con el metastore tradicional de la cuenta Community.
   *   **Use a personal schema for each user working on this project:** Selecciona **`y`** (sí) para que el bundle cree un esquema de datos personal y aislado (`workspace.rbeauxisconsultor`) para tus tablas de prueba, evitando colisiones de desarrollo.
10. **Aplanar la estructura de carpetas (Mover archivos a la raíz):** Si el asistente de Databricks creó tu proyecto en una subcarpeta (por ejemplo, `dbs_project/` o `mi_proyecto_cdc/`), te recomendamos mover todo su contenido a la raíz de tu repositorio de trabajo para mantener una arquitectura plana, limpia y directa. En PowerShell puedes hacerlo corriendo:
    ```powershell
    # Mover archivos de la subcarpeta a la raíz del repositorio
    Get-ChildItem -Path .\dbs_project -Force | Move-Item -Destination .\ -Force -ErrorAction SilentlyContinue;
    # Borrar la subcarpeta ya vacía
    Remove-Item -Path .\dbs_project -Recurse -Force -ErrorAction SilentlyContinue;
    ```
11. **Optimizar y corregir el archivo `.gitignore`:** El asistente de inicialización del bundle creará un `.gitignore` genérico que sobrescribirá tus exclusiones locales. Edita de inmediato este archivo para fusionar las exclusiones de tus entornos virtuales locales (como `.venv311/`, `venv/`, `__builtins__.pyi`), garantizando que Git no rastree archivos pesados.
12. **Inicializar y Conectar tu Repositorio Git de Cero:** Con tu lienzo en blanco estructurado en la raíz, establece tu repositorio Git y conéctalo con tu repositorio remoto de GitHub ejecutando:
    ```powershell
    # 1. Inicializar la base de datos de Git local
    git init

    # 2. Agregar todos tus archivos limpios al área de preparación (stage)
    git add .

    # 3. Crear tu primer commit de infraestructura
    git commit -m "chore: estructura inicial de DAB 100% limpia para AWS Community"

    # 4. Vincular tu repositorio con tu GitHub personal
    git remote add origin https://github.com/rbeauxis/dbricks_repository.git
    ```

### Estructura Típica de Proyecto
Una vez inicializado, el proyecto tendrá la siguiente estructura organizada de archivos y carpetas:

```text
mi_proyecto_cdc/
├── databricks.yml          # El archivo principal de configuración del Bundle
├── bundle.lock.json
├── src/                    # Aquí va tu código fuente (Notebooks, SQL, Python)
│   ├── pipeline_cdc.sql    # Tu script con la lógica APPLY CHANGES INTO
│   └── transformaciones.py # Otros notebooks o scripts auxiliares
└── resources/              # Definición de la infraestructura y recursos
    ├── jobs.yml            # Configuración del Workflow / Horarios de ejecución
    └── pipelines.yml       # Configuración del motor / computación de Delta Live Tables
```

> [!NOTE]
> **💡 ACLARACIÓN CLAVE: Lógica de Datos vs. Infraestructura (¿Por qué DLT no va en `resources/`?):**
> 
> Es común preguntarse por qué el script de Delta Live Tables (DLT) se almacena en `src/` y no en `resources/`. La regla fundamental de Databricks Asset Bundles (DAB) es la **separación de conceptos**:
> 
> 1. **Lógica de Datos (`src/`):** Aquí se aloja el **código puro** en SQL o Python (por ejemplo, `pipeline_cdc.sql` con el `APPLY CHANGES INTO`). Es el código que define *qué* transformaciones y reglas de negocio se aplican a los datos.
> 2. **Configuración de Infraestructura (`resources/`):** Aquí se aloja la **configuración del motor** en archivos YAML (como `pipelines.yml`). Este archivo no procesa datos, sino que le indica a Azure Databricks *cómo* y *dónde* correr el pipeline (tipo de máquinas, escalabilidad, nombre en la UI de Databricks, base de datos destino, etc.), apuntando a tu código de `src/` mediante la propiedad `libraries`.

---

## 8. Configuración Avanzada de DABs en el Entorno Local (VS Code)

Para trabajar de manera 100% profesional e independiente del navegador desde tu máquina local, configura estos elementos esenciales en tu IDE:

### 1. Autocompletado y Validación de Esquema (databricks.yml)
VS Code puede validar sintácticamente tu archivo `databricks.yml` y ofrecerte autocompletado mediante IntelliSense. 
1. Instala la extensión **YAML (Red Hat)** desde el Marketplace de VS Code.
2. Abre o crea el archivo `.vscode/settings.json` en la raíz de tu proyecto e integra la siguiente configuración del esquema oficial de Databricks:
   ```json
   {
       "yaml.schemas": {
           "https://raw.githubusercontent.com/databricks/cli/main/resources/schemas/bundle/bundle.schema.json": ["*databricks.yml", "databricks.yml"]
       }
   }
   ```
   *¡Listo! Ahora tendrás advertencias en tiempo real de campos erróneos y autocompletado inteligente mientras editas la estructura de tus bundles.*

### 2. Vinculación de Perfiles de CLI con el Bundle (databricks.yml)
Tus perfiles de autenticación local se guardan en el archivo `~/.databrickscfg`. Para que el bundle sepa qué credenciales usar, el valor de la clave `profile` en tu target de desarrollo **debe coincidir exactamente** con el perfil con el que iniciaste sesión en la terminal:

*   **En la terminal (Paso 3):**
    ```powershell
    databricks auth login --host https://dbc-7e3d85b9-25a9.cloud.databricks.com --profile community
    ```
*   **En el archivo `databricks.yml`:**
    ```yaml
    targets:
      dev:
        mode: development
        default: true
        workspace:
          host: https://dbc-7e3d85b9-25a9.cloud.databricks.com
          profile: community  # <--- DEBE COINCIDIR EXACTAMENTE CON EL PERFIL DEL CLI
    ```

> [!WARNING]
> **⚠️ REGLA DE ORO DE SEGURIDAD (Obligatorio indicar el Perfil):**
> 
> Es una práctica de seguridad fundamental e innegociable **especificar siempre la propiedad `profile` de forma explícita dentro de cada target** en tu `databricks.yml`. 
> 
> Si omites la clave `profile` en la configuración de tus targets, Databricks CLI recurrirá de forma silenciosa al perfil local marcado como `(Default)`. Si trabajas con múltiples clientes o cuentas en tu PC, corres el riesgo crítico de que un comando de prueba despliegue accidentalmente recursos y datos en el Workspace de producción o de otra empresa por error. *Indicar el perfil explícitamente es tu escudo de seguridad.*

### 3. Gestión de Perfiles por Defecto y Sesiones Expiradas (Tokens Inválidos)
El CLI de Databricks tiene un perfil marcado como **`(Default)`** (que suele ser el primero con el que inicias sesión o tu correo principal). Al correr comandos generales de inicialización de bundles (como `databricks bundle init`), el CLI intentará usar este perfil por defecto de forma automática.

Si recibes el error:
> `Error: A new access token could not be retrieved because the refresh token is invalid.`

Significa que tu sesión web local en esa cuenta ha caducado. Para solucionarlo de inmediato y refrescar tus accesos, corre:
```powershell
databricks auth login --profile <tu-nombre-de-perfil>
# Ejemplo: databricks auth login --profile rbeauxisconsultor@gmail.com
```
*Esto abrirá el navegador para re-autenticar la sesión y dejar el token activo (`Valid: YES`) de inmediato.*

---

## 9. El Flujo de Trabajo Profesional Unificado: Git + Databricks Asset Bundles (DAB)

En un entorno de ingeniería de datos moderno y profesional, **Git** y **DAB** no compiten, sino que se complementan de manera perfecta en un flujo de **CI/CD (Integración y Despliegue Continuos)**:

- **Git** es la fuente única de verdad para el código y la configuración (se encarga del control de versiones, ramas, revisiones por pares y Pull Requests).
- **DAB** es el motor que traduce ese código y configuraciones YAML en recursos reales ejecutándose en Databricks (se encarga del despliegue, sincronización y validación).

> [!IMPORTANT]
> **⚠️ REGLA DE ORO DEL DESARROLLO (Orden de Ejecución Obligatorio):**
> 
> El flujo de trabajo exige un orden estricto de pasos para evitar "contaminar" el repositorio de Git con código roto:
> 1.  **Primero se testea con DABs:** Despliegas tu código y tus recursos de prueba en la nube usando `databricks bundle deploy` o `sync` para certificar en Databricks Web que todo corre y compila perfectamente de extremo a extremo.
> 2.  **Luego se sube a Git:** Una vez (y solo cuando) la prueba en el Workspace web haya sido **100% exitosa**, procedes a registrar tus cambios en Git (`git commit`) y enviarlos a GitHub (`git push`).
> 
> *Nunca subas código al repositorio remoto que no haya sido previamente validado y ejecutado con éxito en Databricks mediante DAB.*

### Arquitectura del Flujo de Trabajo

```mermaid
graph TD
    subgraph Local [1. Estación Local (VS Code)]
        A[Escribir Código src/ y recursos resources/] -- git push --> B[Rama de Git feature/*]
        A -- databricks bundle sync/deploy --> C[(Sandbox Personal /Users/usuario/.bundle/...)]
    end
    subgraph VersionControl [2. Repositorio GitHub]
        B -- Pull Request --> D{Revisión & Validación}
        D -- Merge to main --> E[Rama main de GitHub]
    end
    subgraph Pipeline [3. Automatización CI/CD]
        E -- GitHub Actions --> F[databricks bundle deploy -t prod]
    end
    subgraph Production [4. Entorno de Producción Databricks]
        F -- Actualiza / Crea --> G[(Jobs y Pipelines DLT de Producción)]
    end
```

*(Representación gráfica en texto plano)*
```text
1. Estación Local (VS Code)
   ┌──────────────────────────────────────────────┐
   │   Código fuente (src/) e Infra (resources/)   │
   └──────┬────────────────────────────────┬──────┘
          │                                │
   databricks bundle sync          git commit / push
          │                                │
          ▼                                ▼
   ┌──────────────────────────────┐ ┌──────────────────────────────┐
   │  Sandbox Dev en Databricks   │ │   GitHub: Rama feature/*     │
   │  (/Users/usuario/.bundle/..) │ └──────────────┬───────────────┘
   └──────────────────────────────┘                │
                                            Pull Request & PR Merge
                                                   │
                                                   ▼
                                    ┌──────────────────────────────┐
                                    │    GitHub: Rama main         │
                                    └──────────────┬───────────────┘
                                                   │
                                            GitHub Actions (CI/CD)
                                                   │
                                                   ▼
                                    ┌──────────────────────────────┐
                                    │ databricks bundle deploy     │
                                    │ -t prod                      │
                                    └──────────────┬───────────────┘
                                                   │
                                                   ▼
                                    ┌──────────────────────────────┐
                                    │   Producción en Databricks   │
                                    │   (Jobs y Pipelines DLT)     │
                                    └──────────────────────────────┘
```

### Reglas Clave de Convivencia (Git + DAB)

1. **Archivos a Sincronizar en Git (Commitear):**
   *   Toda tu lógica en `src/` (SQL, notebooks, scripts de Python).
   *   Toda la infraestructura descrita en YAML en `resources/` (definiciones de workflows, schedules, DLT pipelines).
   *   El archivo de configuración principal `databricks.yml`.
   *   El archivo de seguimiento `bundle.lock.json` (es importante subirlo a Git ya que mantiene un registro de los IDs de los recursos que DAB despliega en cada target).
2. **Archivos a Ignorar en Git (Añadidos en .gitignore):**
   *   La carpeta de caché `.databricks/` que genera el CLI localmente al construir y sincronizar.
   *   Los entornos virtuales locales (como `venv/` o `.venv311/`).
   *   Tus credenciales y llaves secretas (el archivo `~/.databrickscfg` reside en tu directorio de usuario en tu PC y NUNCA se sube al repositorio).
   *   Cualquier archivo de sobreescritura local como `databricks.local.yml`.

---

## Anexo: Gestión de Múltiples Proveedores Git

Es común trabajar con **GitHub** y **Bitbucket** simultáneamente en la misma máquina. Git gestiona esto de forma segura y aislada:

### 1. Aislamiento por Repositorio
Cada carpeta de proyecto tiene su propia URL de destino (`remote`). Puedes verificarla con `git remote -v`.

### 2. Gestión de Credenciales
Windows utiliza el **Git Credential Manager**, que guarda las "llaves" por dominio. Las credenciales de `github.com` nunca se envían a `bitbucket.org`.
