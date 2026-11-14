# Archetype Nolly X Preset Editor

Un programa en Python puro, construido desde cero a partir de la especificación y código fuente del framework **JUCE** (`juce_ValueTree.cpp`, `juce_Variant.cpp`, `juce_InputStream.cpp` y `juce_OutputStream.cpp`), capaz de leer, inspeccionar, editar y serializar los archivos de preset `.xml` de **Archetype Nolly X** con **fidelidad byte a byte (100% roundtrip bit-for-bit)**.

El proyecto está gestionado con [uv](https://docs.astral.sh/uv/).

---

## 🎸 Contexto técnico: ¿Qué son estos archivos `.xml`?

A pesar de su extensión `.xml`, los presets de Archetype Nolly X (y de otros plugins de Neural DSP) no son texto plano ni XML estándar. Son streams binarios de la estructura interna **`juce::ValueTree`** serializada con `ValueTree::writeToStream()` y `var::writeToStream()`:

1. **Tag del nodo**: String UTF-8 terminado en `\0` (ej. `"nolly-x"`).
2. **Número de propiedades**: Entero comprimido variable (`InputStream::readCompressedInt()`).
3. **Pares propiedad-valor**:
   - Nombre de la propiedad (string UTF-8 terminado en `\0`).
   - Valor tipado `juce::var`:
     - Marcador de tipo (`varMarker_Int=1`, `varMarker_BoolTrue=2`, `varMarker_BoolFalse=3`, `varMarker_Double=4`, `varMarker_String=5`, `varMarker_Int64=6`, `varMarker_Array=7`, `varMarker_Binary=8`).
     - Payload del valor según el tipo (longitud empaquetada o fija en little-endian).
4. **Hijos del nodo**: Número de nodos hijos (entero comprimido) seguido recursivamente por cada subárbol.

Este programa implementa completamente estos serializadores y deserializadores sin dependencias externas pesadas.

---

## 🚀 Requisitos e Instalación

Solo necesitas tener `uv` instalado (o Python 3.11+).

```bash
cd preset_editor
uv sync
```

---

## ⚡ Novedad: Herramienta Unificada `nolly.cmd` (Para IAs y Guitarristas)

En la raíz del repositorio se incluye el comando ultra-rápido `nolly.cmd` (ejecutable en ~0.25s) que automatiza la búsqueda, generación en un solo paso, verificación e informe de potenciómetros:

```bash
# 1. Búsqueda instantánea en catálogo
.\nolly.cmd search "metal" --amp rhythm

# 2. Creación atómica de tono (clona base, edita, compila XML+YML, valida y genera informe)
.\nolly.cmd create --base "All-Purpose Metal Rhythm" \
                   --song "Tool - Lateralus" \
                   --num "00" \
                   --name "Main Drop D Riff" \
                   --set "rhythmGain=0.72" "rhythmBass=0.6" "rhythmPresence=2:30" "gateThreshold=-65"

# 3. Inspección detallada con tabla de reloj y escala 0-10
.\nolly.cmd inspect "User/Tool - Lateralus/00 - Main Drop D Riff.xml"
```

---

## 🛠️ Uso por Línea de Comandos (CLI)

Todos los comandos se pueden ejecutar cómodamente usando `uv run python main.py <comando>` desde la carpeta `preset_editor`:

### 1. Ver resumen del preset (`info`)
Muestra el ampli seleccionado, pantallas, puerta de ruido y pedales activos:
```bash
uv run python main.py info ../Default.xml
```

### 2. Inspeccionar todos los parámetros (`dump`)
Muestra los valores de todos los parámetros organizados por secciones (Ampli, Puerta, Overdrive, Delay, Reverb, etc.). Para los potenciómetros (0.0 a 1.0) muestra automáticamente la escala de 0 a 10 y la posición en el reloj (7:00 a 5:00):
```bash
# Volcar todo el preset
uv run python main.py dump ../Default.xml

# Filtrar por sección (ej. solo overdrive, ampli o reverb)
uv run python main.py dump ../Default.xml -s overdrive
uv run python main.py dump ../Default.xml -s rhythm
uv run python main.py dump ../Default.xml -s reverb
```

### 3. Consultar un parámetro específico (`get`)
```bash
uv run python main.py get ../Default.xml rhythmGain
uv run python main.py get ../Default.xml overdrive1Level
```

### 4. Modificar un parámetro (`set`)
Modifica un parámetro existente (puedes sobreescribir el archivo o guardar en una ruta nueva con `-o`):
```bash
# Cambiar el nombre del preset
uv run python main.py set ../Default.xml name "Mi Tono Personal" -o ../User/MiTono.xml

# Activar el Overdrive 1 y ajustar ganancia
uv run python main.py set ../User/MiTono.xml overdrive1Active true
uv run python main.py set ../User/MiTono.xml rhythmGain 0.75
```

### 5. Modificar múltiples parámetros a la vez (`set-many`)
```bash
uv run python main.py set-many ../User/MiTono.xml \
    overdrive1Active=true \
    overdrive1Drive=0.4 \
    rhythmGain=0.68 \
    rhythmTreble=0.55 \
    -o ../User/MiTono.xml
```

### 6. Duplicar y editar un preset existente (`copy-edit`)
La forma más rápida y recomendada para crear nuevos presets a partir de los de fábrica:
```bash
uv run python main.py copy-edit \
    --name "Deftones Heavy Rhythm" \
    ../Default.xml \
    "../User/Deftones - Be Quiet and Drive/00 - Heavy Riff.xml" \
    overdrive1Active=true \
    overdrive1Level=0.7 \
    rhythmGain=0.8
```

### 7. Comparar dos presets (`diff`)
Muestra en una tabla clara qué parámetros difieren entre dos archivos de preset:
```bash
uv run python main.py diff ../Default.xml "../User/Deftones - Be Quiet and Drive (Far Away)/00 - Heavy Riff and Chorus.xml"
```

### 8. Exportar e importar a YAML / YML (`to-yaml` / `from-yaml`)
El formato **YAML** es ideal para humanos: legible, limpio y fácilmente editable en cualquier editor:
```bash
# Exportar de XML a YAML
uv run python main.py to-yaml ../Default.xml -o default.yml
# (o el alias to-yml)
uv run python main.py to-yml ../Default.xml -o default.yml

# Reconvertir de YAML a XML nativo de Nolly X
uv run python main.py from-yaml default.yml ../User/MiTonoDesdeYaml.xml
# (o el alias from-yml)
uv run python main.py from-yml default.yml ../User/MiTonoDesdeYaml.xml
```

### 9. Exportar e importar a JSON (`to-json` / `from-json`)
Permite exportar el preset completo a un archivo JSON editable y volver a convertirlo en el formato `.xml` nativo de Nolly X:
```bash
# Exportar a JSON
uv run python main.py to-json ../Default.xml -o default.json

# Importar de JSON a preset XML
uv run python main.py from-json default.json nuevo_preset.xml
```

### 10. Validar fidelidad byte a byte (`validate`)
Verifica automáticamente que todos los presets `.xml` se puedan convertir a YAML y reconvertir a XML con 100% de exactitud binaria:
```bash
uv run python main.py validate
```

---

## 🐍 Uso desde Python (Librería)

También puedes usarlo directamente en scripts o notebooks de Python:

```python
from preset_editor import NollyPreset, value_to_clock

# 1. Cargar preset
preset = NollyPreset.load("../Default.xml")

# 2. Consultar información
print(f"Preset: {preset.name}")
print(f"Ampli activo: {preset.selected_amp_name}")

# 3. Leer un potenciómetro
gain = float(preset.get_parameter("rhythmGain"))
print(f"Gain: {gain * 10.0}/10 (Reloj: ~{value_to_clock(gain)})")

# 4. Modificar valores
preset.name = "Lead Solos"
preset.selected_amp_id = 3  # 0=Clean, 1=Crunch, 2=Rhythm, 3=Lead
preset.set_parameter("leadGain", "0.75")
preset.set_parameter("overdrive1Active", "true")
preset.set_parameter("postDelayActive", "true")

# 5. Guardar en un nuevo archivo
preset.save("../User/Lead Solos.xml")
```

---

## 🧪 Pruebas Automatizadas

El proyecto incluye tests unitarios con `pytest` que verifican la fidelidad de serialización byte a byte en **los 246 presets de Archetype Nolly X**:

```bash
uv run pytest
```
