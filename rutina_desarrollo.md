# Rutina de Desarrollo Diario - Databricks Certified Data Engineer Associate

Guía rápida para iniciar y operar tu entorno de desarrollo.

---

## 1. Inicio de Sesión (Checklist)

```
[ ] 1. Abrir VS Code en c:\Users\rodri\repo_snowflake\databricks
[ ] 2. Levantar el cluster DemoCluster (Panel Databricks → ▶)
[ ] 3. Asegurar que el intérprete activo es `.venv` (creado con uv) en la barra inferior de VS Code
[ ] 4. Confirmar que el cluster está conectado en la extensión Databricks (icono verde)
[ ] 5. Confirmar que tienes un archivo `.env` configurado localmente.
```

---

## 2. El Ciclo de Trabajo Profesional

Este es el flujo recomendado para mantener tu código seguro y sincronizado.

### Paso A: Editar en VS Code
- Crea o modifica archivos `.py` o `.sql` de lógica de datos.
- **💡 Lógica vs. Infraestructura (DAB):** Si trabajas con Asset Bundles, escribe tu código de datos (como scripts DLT o transformaciones Spark) dentro de `src/`. El YAML en `resources/pipelines.yml` es puramente para configurar el motor en Databricks (computación, nombres de base de datos) y solo apunta a tus archivos en `src/` a través de `libraries`. ¡No pongas código SQL o Python dentro de `resources/`!
- Asegúrate de incluir `# Databricks notebook source` en la primera línea de tus notebooks `.py`.
- Para referenciar otros notebooks, usa `# MAGIC %run ./ruta/relativa/Notebook` (el `%run` es nativo de Databricks y **no se emula localmente**).
- El linter puede marcar variables inyectadas por `%run` (e.g., `full_name`) como "no definidas". Esto es un falso positivo — el archivo `__builtins__.pyi` en la raíz del proyecto declara los globals de Databricks para silenciarlo.

### Paso B: Push a GitHub
Cuando estés listo para probar en el cluster o guardar tu progreso:
```powershell
git add .
git commit -m "Explica qué cambiaste"
git push
```

### Paso C: Pull en Databricks Web (Sincronizar)
1. Abre Databricks en el navegador.
2. Ve a **Workspace** → **Repos** → **`dbricks_repository`**.
3. Haz clic en el nombre de la rama (**`main`**) en la esquina superior izquierda.
4. En el panel que aparece, haz clic en el botón **Pull**.
5. Los cambios aparecerán instantáneamente.

---

## 3. Gestión de Ramas (Branches)

Para trabajar en funcionalidades nuevas sin afectar la rama principal:

### Crear rama en VS Code:
```powershell
git checkout -b feature/mi-nueva-tarea
# Hacer cambios...
git add .
git commit -m "Mi avance"
git push -u origin feature/mi-nueva-tarea
```

### Cambiar de rama en Databricks:
1. Clic en el nombre de la rama actual (**`main`**) arriba a la izquierda.
2. Clic en **"Checkout"** o busca la rama en la lista de remotes.
3. Selecciona `feature/mi-nueva-tarea`.
4. Databricks cambiará todos los archivos a esa versión automáticamente.

> **Tip:** Siempre haz el merge de tus ramas en GitHub (vía Pull Request) y luego haz `Pull` en Databricks en la rama `main` para actualizar todo.

---

## 4. Coexistencia y Sincronización (¿Cómo evitar conflictos?)

Es fundamental entender los tres flujos disponibles para evitar que tus herramientas locales interfieran con la carpeta compartida en **Databricks Repos** y provoquen bloqueos al hacer `git pull`.

### A. El Flujo de Repos Git (Interactivos)
*   **Destino en Workspace:** `/Workspace/Repos/<usuario>/dbricks_repository`
*   **Cómo operar:** Modifica en tu VS Code local, sube con `git push` a GitHub, y haz un `Pull` manual en la UI de Databricks Web.
*   **⚠️ RECOMENDACIÓN CRÍTICA:** Mantén el **"Sync Folder"** de la extensión de VS Code en **STOPPED** si estás trabajando directamente sobre la carpeta `/Repos/`. Si habilitas el sync automático sobre esta ruta, subirás archivos locales directamente al repo interactivo, generando archivos modificados/no guardados que te impedirán hacer un `git pull` de GitHub.

### B. El Flujo de Databricks Asset Bundles (DAB)
*   **Destino en Workspace:** `/Users/<usuario>/.bundle/<nombre-proyecto>/dev/files/...` (Ruta aislada y segura).
*   **Cómo operar:** Escribe código y despliega o sincroniza usando la CLI de Databricks:
    ```powershell
    # Despliegue único
    databricks bundle deploy -t dev
    
    # Sincronización en tiempo real (modo desarrollo continuo)
    databricks bundle sync -t dev --watch
    ```
*   **Ventaja:** Al usar una ruta aislada en `/Users/`, **puedes activar la sincronización automática en tiempo real de DAB sin temor** a romper tu flujo de Git ni generar conflictos en la carpeta compartida de `/Repos/`.

### C. Ejecución de Celdas Interactiva (Databricks Connect)
*   Al abrir un archivo `.py` en VS Code (formateado como notebook) y presionar `Run Cell` o usar el botón **▶ "Run current file with Databricks Connect"**:
    *   La extensión de VS Code sube de forma transparente y temporal tu código a `/Users/<usuario>/.ide-extension-system/...` para ser ejecutado directamente en `DemoCluster`.
    *   Este flujo es completamente seguro y **no interfiere** con tus archivos locales ni con tu repositorio de Git en Databricks.

---

## 5. Operativa y Ciclo de Vida 100% Local con DABs

Trabajar con **Databricks Asset Bundles (DAB)** te permite desvincularte por completo del navegador Web de Databricks. Toda la validación, empaquetado, despliegue, ejecución de tareas y destrucción de recursos se puede controlar de forma local desde tu terminal de VS Code:

### A. Validación de la Configuración Local
Antes de subir cualquier recurso, comprueba que la estructura YAML y las rutas de tu bundle sean correctas sin necesidad de subir nada:
```powershell
databricks bundle validate
```
*   **Qué hace:** Analiza localmente tus archivos de configuración (`databricks.yml`, `resources/*.yml`), verifica el JSON Schema de Databricks y reporta errores sintácticos o de configuración.

### B. Despliegue de Recursos
Sube tus archivos de código y compila/crea tus recursos (Jobs, Delta Live Tables Pipelines) directamente en el entorno de desarrollo:
```powershell
databricks bundle deploy -t dev
```
*   **Qué hace:** Compila y sube tus notebooks/archivos `.py` o `.sql` a tu espacio de desarrollo personal en Databricks y aprovisiona automáticamente tus Jobs y Pipelines.
*   **⚠️ REGLA DE SEGURIDAD OBLIGATORIA (Especificar Target y Perfil):**
    *   **Especificar Target (`-t dev`):** Aunque en `databricks.yml` exista un target predeterminado, **nunca dependas del comportamiento implícito**. Especifica siempre de forma explícita el parámetro `-t <entorno>` en tus comandos (ej. `databricks bundle deploy -t dev`). Esto evita que un cambio accidental en tu archivo de configuración despliegue en producción o sobreescriba recursos equivocados.
    *   **Especificar Perfil (`profile`):** Asegúrate de que la propiedad `profile` esté indicada de forma explícita en cada target dentro de tu `databricks.yml`. Si omites indicar el perfil, el CLI de Databricks usará por defecto el perfil marcado como `(Default)`. Si trabajas con múltiples clientes o cuentas en tu PC, corres el riesgo de desplegar por error en el Workspace equivocado. *El perfil explícito es tu escudo.*
*   **💡 PROTECCIONES AUTOMÁTICAS DEL MODO DESARROLLO (`mode: development`):**
    Cuando compilas bajo el target `dev` (que tiene activado el modo de desarrollo en `databricks.yml`), Databricks CLI activa de forma transparente tres salvaguardas esenciales:
    1.  **Aislamiento Total:** Todo se despliega en tu directorio personal de usuario en el Workspace (ej: `/Users/tu_usuario/.bundle/...`), garantizando que no pises el trabajo de ningún compañero.
    2.  **Sufijos de Seguridad:** Los recursos creados (como Pipelines DLT) incluirán tu identificador de usuario para distinguirlos visualmente.
    3.  **Pausa de Costos en la Nube:** Databricks **pausará automáticamente todos los horarios (schedules), disparadores (triggers) y ejecuciones continuas** de tus Jobs y pipelines. De este modo, evitas consumir créditos de cómputo en la nube de forma accidental en segundo plano cuando no estás trabajando.

### C. Ejecución de Recursos desde la Terminal Local
Puedes iniciar y monitorear la ejecución de tus recursos directamente desde tu máquina local sin abrir el navegador:
*   **Ejecutar un Workflow (Job):**
    ```powershell
    databricks bundle run -t dev <nombre-del-job>
    ```
    *   *Nota:* Reemplaza `<nombre-del-job>` con la clave de tu recurso (por ejemplo, `mi_proyecto_cdc_job` definido en `resources/jobs.yml`). Esto iniciará el workflow y transmitirá los registros y el estado de la ejecución directamente a tu consola de VS Code.
*   **Ejecutar/Refrescar una Delta Live Table (Pipeline DLT):**
    ```powershell
    databricks bundle run -t dev <nombre-del-pipeline>
    ```
    *   *Nota:* Esto iniciará una actualización (Update) del pipeline DLT definido en `resources/pipelines.yml` y te permitirá ver el estado del refresco desde tu terminal local.

### D. Sincronización Interactiva Directa (Desarrollo Rápido)
Si estás en una sesión de desarrollo continuo, puedes mantener los archivos sincronizados en tiempo real a medida que guardas en VS Code:
```powershell
databricks bundle sync -t dev --watch
```
*   **Qué hace:** Mantiene un listener de archivos local. Cada vez que guardas un cambio en tu editor, se sube en menos de un segundo al Workspace, permitiendo pruebas instantáneas sin necesidad de ejecutar comandos manuales de deploy.

### E. Destrucción de Recursos (Teardown & Limpieza Local)
Una vez que hayas terminado tus pruebas de desarrollo y quieras evitar el consumo innecesario de créditos cloud o mantener tu Workspace ordenado:
```powershell
databricks bundle destroy -t dev
```
*   **Qué hace:** Elimina **completamente** todos los recursos creados por tu bundle en Databricks (Jobs, Pipelines de Delta Live Tables y los archivos cargados bajo la ruta `root_path`). *Es el comando perfecto para mantener tu área de desarrollo limpia y libre de costos.*

---

## 6. El Ciclo de Desarrollo Diario Unificado (Git + DAB)

El flujo de trabajo óptimo y profesional para ingenieros de datos combina la velocidad de la iteración local con la seguridad del control de versiones. Sigue este ciclo paso a paso cada día:

> [!IMPORTANT]
> **⚠️ REGLA DE ORO DEL DESARROLLO (Orden Obligatorio):**
> 
> *   **Primero se testea con DABs:** Modificas tus fuentes y utilizas `databricks bundle deploy` o `sync` para compilar y probar tus cambios en el entorno real de Databricks, certificando que el pipeline y los datos corren con éxito.
> *   **Luego se sube a Git:** Solo cuando hayas verificado visual y operacionalmente en Databricks Web que tu pipeline funciona al 100%, realizas el `git commit` y `git push` para guardar tu avance en GitHub.
> 
> *¡Nunca envíes código al repositorio remoto que no haya sido ejecutado y validado en la nube con DABs primero!*

### Paso 1: Sincronizar el repositorio y crear una rama de trabajo
Antes de empezar a escribir código, asegúrate de estar en la última versión de la rama principal y crea tu propia rama:
```powershell
git checkout main
git pull
git checkout -b feature/mi-nueva-tarea
```

### Paso 2: Activar el entorno de desarrollo local y la sincronización (DAB)
1. Abre VS Code en tu carpeta de proyecto.
2. Inicia la sincronización automática de tu bundle para subir cambios en tiempo real a tu sandbox personal en Databricks sin interferir con Git:
   ```powershell
   databricks bundle sync -t dev --watch
   ```
3. Trabaja en tus archivos locales de código en `src/` (SQL, Python) y de recursos en `resources/`. Cada vez que presiones `Ctrl + S`, el CLI subirá tus archivos al sandbox inmediatamente.

### Paso 3: Validar y Desplegar
Si has modificado tus archivos de recursos YAML (por ejemplo, agregando un Job o modificando la configuración de Delta Live Tables), valida tu sintaxis localmente y realiza un despliegue completo de la infraestructura de desarrollo:
```powershell
# Comprobar sintaxis
databricks bundle validate

# Desplegar jobs/pipelines de desarrollo
databricks bundle deploy -t dev
```

### Paso 4: Ejecutar Pruebas Locales (Terminal)
Prueba la lógica de tus tareas y flujos directamente desde tu consola de VS Code para validar que el pipeline corre de forma exitosa en la nube:
```powershell
databricks bundle run -t dev mi_proyecto_cdc_job
```

### Paso 5: Confirmar cambios y enviar a GitHub (Git)
Una vez que el pipeline ha sido verificado y todo funciona perfectamente de extremo a extremo, detén el proceso de `watch` (`Ctrl + C` en la terminal), limpia los recursos de prueba si lo deseas (`databricks bundle destroy -t dev`), y sube tus cambios al repositorio:
```powershell
# Guardar progreso en tu rama
git add .
git commit -m "feat: implementacion del pipeline de cdc y delta live tables"
git push -u origin feature/mi-nueva-tarea
```

### Paso 6: Pull Request y Despliegue en Producción (CI/CD)
1. Abre tu repositorio en GitHub y crea un **Pull Request (PR)** desde tu rama `feature/mi-nueva-tarea` hacia `main`.
2. Una vez aprobado y fusionado (merged), la automatización de CI/CD (GitHub Actions) ejecutará de forma automática en el servidor:
   ```bash
   databricks bundle deploy -t prod
   ```
   Esto creará/actualizará los Jobs y pipelines del entorno productivo, garantizando que el entorno real de producción sea un reflejo exacto de la única fuente de verdad: el código aprobado en Git.

---

## 7. Solución de Problemas Comunes

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: No module named 'google.protobuf'` | Versión de `protobuf` incompatible. Corre `uv sync` o instala explícitamente: `pip install "protobuf<5.0.0,>=4.25.8"` |
| `databricks-connect package is not installed` | VS Code está apuntando al Python global o a un `venv` roto. Asegúrate de elegir la ruta `${workspaceFolder}\.venv\Scripts\python.exe` y haber corrido `uv sync`. |
| Error instalando con `pip install -e .[dev]` | Nuestro `pyproject.toml` usa `[dependency-groups]` (estándar de `uv`). Si usas `pip` directo, instalará la app pero no las herramientas de desarrollo. Usa `uv sync` o instala `databricks-connect` manualmente. |
| VS Code pide `ipykernel` | Ejecuta: `uv pip install ipykernel` (o `pip install ipykernel` en tu venv activo) |
| Linter marca variables de `%run` como indefinidas (e.g. `full_name`) | Es un falso positivo esperado. El archivo `__builtins__.pyi` en la raíz del proyecto mitiga esto para los globals de Databricks. Las variables de `%run` no tienen solución estática perfecta. |
| No veo los botones `Run Cell` | Asegúrate que el archivo tenga `# Databricks notebook source` en la línea 1 y que la extensión Databricks esté activa. |
| El cluster no arranca | Revisa el límite de cuota en tu suscripción de Azure o reinicia el cluster desde la Web UI. |
| `Error: A new access token could not be retrieved because the refresh token is invalid.` | Tu token de sesión local ha expirado. Re-autentica tu perfil corriendo: `databricks auth login --profile <nombre-perfil>` (ej. `databricks auth login --profile rbeauxisconsultor@gmail.com`). |
