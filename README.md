# 🎸 Archetype Nolly X Tone Suite & Preset Engine

Suite integral de herramientas en Python puro para gestión, búsqueda, ingeniería inversa, creación atómica de tonos e integración con asistentes de Inteligencia Artificial (Antigravity / LLMs) para **Archetype Nolly X** (Neural DSP).

Serializa y deserializa la estructura binaria interna de **JUCE `ValueTree`** con fidelidad byte a byte (100% roundtrip bit-for-bit), y proporciona utilidades de alta velocidad en formato YAML para interactuar con presets en milisegundos.

---

## ⚡ Instalación y Restauración en 1 Solo Comando

Si reinstalas Archetype Nolly X o cambias de equipo, puedes descargar y restaurar toda la herramienta, las instrucciones de IA (`AGENTS.md`), el catálogo de presets y tus tonos de usuario con **un solo comando en PowerShell**:

```powershell
irm https://raw.githubusercontent.com/JorgeRuizDev/archetype-nolly-x/main/install.ps1 | iex
```

### ¿Qué hace este comando automáticamente?
1. Detecta o inicializa el directorio oficial de presets de Windows (`C:\ProgramData\Neural DSP\Archetype Nolly X`).
2. Configura los permisos de Git (`safe.directory`) para evitar bloqueos de seguridad en `ProgramData`.
3. Descarga y sincroniza la herramienta completa + `AGENTS.md` + catálogo YAML + presets de canciones en `User/` (respetando los presets originales del instalador de Nolly).
4. Configura el entorno virtual con `uv` o `python`.
5. Ejecuta una prueba de validación y deja `.\nolly.cmd` listo para usar.

---

## 💻 Instalación Manual con Git

Si prefieres usar Git directamente desde la terminal:

### Opción A: Tras haber reinstalado Nolly (el directorio ya existe con presets de fábrica)
```cmd
cd /d "%ProgramData%\Neural DSP\Archetype Nolly X"
git config --global --add safe.directory "C:/ProgramData/Neural DSP/Archetype Nolly X"
git init -b main
git remote add origin https://github.com/JorgeRuizDev/archetype-nolly-x.git
git fetch origin main
git checkout -f main
uv sync
```

### Opción B: En una máquina limpia (antes de instalar Nolly)
```cmd
git clone https://github.com/JorgeRuizDev/archetype-nolly-x.git "%ProgramData%\Neural DSP\Archetype Nolly X"
cd /d "%ProgramData%\Neural DSP\Archetype Nolly X"
uv sync
```

---

## 🚀 Flujo de Trabajo Rápido (`nolly.cmd`)

El script `.\nolly.cmd` en la raíz ejecuta cualquier comando en ~0.25 segundos usando el entorno virtual `.venv`:

### 1. Búsqueda instantánea en catálogo
```cmd
.\nolly.cmd search "metal" --amp rhythm
.\nolly.cmd search "clean"
```

### 2. Creación y validación de tono en 1 paso
Clona un preset base, aplica parámetros (admite valores decimales, escala 0–10 y notación de reloj), compila tanto `.xml` como `.yml`, valida la integridad binaria e imprime el reporte para guitarra:

```cmd
.\nolly.cmd create --base "All-Purpose Metal Rhythm" --song "Tool - Lateralus" --num "00" --name "Main Drop D Riff" --set "rhythmGain=0.72" "rhythmBass=7.5/10" "rhythmPresence=2:30" "gateThreshold=-65"
```

### 3. Inspección detallada con escala de reloj y 0-10
```cmd
.\nolly.cmd inspect "User/Tool - Lateralus/00 - Main Drop D Riff.xml"
```

---

## 🤖 Integración con Asistentes IA (`AGENTS.md`)

Este repositorio incluye [AGENTS.md](AGENTS.md), que define las especificaciones exactas para que modelos de IA (Antigravity, Cursor, Claude Code, etc.) generen presets para tu equipamiento específico (ej. Fender Stratocaster SSS, Scarlett Solo, afinaciones Drop D / E Standard).

Las reglas organizativas garantizan:
- Salida en `.\User\<Banda> - <Canción>\XX - <Nombre>.xml` y `.yml`.
- Representación obligatoria de potenciómetros en **horas de reloj** (7:00 a 5:00) y **escala 0 a 10** (el plugin no muestra números en sus potenciómetros).

---

## 🐍 Uso de la API de Python

El paquete es completamente importable sin configurar `sys.path`:

```python
from nolly import NollyPreset, value_to_clock, clock_to_value, scale10_to_value

# Carga polimórfica (.xml o .yml)
preset = NollyPreset.load(r".\yml\Nolly\All-Purpose Metal Rhythm.yml")

# Modificación inteligente
preset.set_parameter("rhythmGain", "2:30")     # Convierte posición de reloj a valor float
preset.set_parameter("rhythmBass", "7.0/10")   # Convierte escala 0-10 a float
preset.set_parameter("gateActive", "true")

# Guardado dual
preset.save(r".\User\Mi Banda - Cancion\00 - Riff.yml")
preset.save(r".\User\Mi Banda - Cancion\00 - Riff.xml")

# Reporte formateado en Markdown
print(preset.generate_tone_report(song="Mi Banda - Cancion", preset_num="00"))
```

---

## 🧪 Tests

Ejecución de la suite de pruebas unitarias (15 tests de fidelidad roundtrip byte a byte y parsing):

```cmd
uv run pytest
```

---

## 📁 Estructura del Repositorio

```text
├── AGENTS.md            # Instrucciones del sistema y reglas para agentes IA
├── README.md            # Esta documentación
├── install.ps1          # Instalador / sincronizador en 1 línea para PowerShell
├── nolly.py             # Entrypoint y shim del módulo raíz
├── nolly.cmd            # Ejecutable de línea de comandos para Windows
├── xml2yml.cmd          # Conversor XML a YAML
├── yml2xml.cmd          # Conversor YAML a XML
├── pyproject.toml       # Definición del paquete Python y dependencias
├── uv.lock              # Lockfile de dependencias reproducibles
├── preset_editor/       # Código fuente del parser JUCE ValueTree y motor de presets
│   ├── cli.py           # CLI unificada (search, create, inspect)
│   ├── juce_valuetree.py# Serializador binario JUCE puro
│   ├── nolly_preset.py  # Modelado del preset y conversiones reloj/escala
│   └── tests/           # Tests unitarios pytest
├── yml/                 # Catálogo completo de presets de fábrica convertidos a YAML
└── User/                # Presets de usuario organizados por canciones
```
