# Agente de resumen diario de IA

Proyecto de ejemplo para seleccionar hasta **un paper y una noticia** sobre IA, LLM, agentes o infraestructura, producir HTML/PDF y, sólo con autorización explícita, enviar correo y publicar un estado en Slack. El modelo local evalúa candidatos; la deduplicación, la ventana horaria y el envío son deterministas. Una etiqueta roja **no** descarta una pieza: se conserva si es nueva y elegible. Los fallos de fuente bloquean el correo con el informe; una corrida con salida autorizada aún puede publicar un estado de fallo en Slack.

**Estado de esta copia:** ejemplo independiente de la instalación operativa. No contiene cuentas, claves, historial de envío, reportes ni configuración operativa. El código exportado pasó 173 pruebas tanto en Ubuntu 24.04 ARM64 como en macOS. Una corrida Linux anterior sin envío con las siete fuentes públicas y Ollama local precargado (`qwen3:4b`) generó HTML/PDF, seleccionó una noticia y ningún paper elegible, registró cero errores de fuente y dejó cero entregas pendientes/enviadas. Una nueva corrida aislada de esta revisión seleccionó un paper y una noticia y generó HTML/PDF, pero la auditoría quedó en estado **failed** con un error de fuente y cero entregas pendientes/enviadas; un diagnóstico separado encontró HTTP 403 en un artículo de OpenAI, aunque la auditoría inicial no registró cuál enlace falló. Una corrida aún anterior sumó 40 errores de consulta de fechas arXiv; las consultas y corridas completas posteriores no los reprodujeron, por lo que se desconoce la causa exacta. Este modelo pequeño, ejecutado en CPU, también agotó el tiempo de espera y produjo un resumen demasiado largo en otras pruebas: ni los artefactos generados ni las pruebas unitarias demuestran rendimiento estable o validan Composio, Gmail o Slack desde la copia limpia. La ruta de entrega se ejercitó en la instalación privada.

## Inicio seguro

- Python 3.10+, `uv` o `pip`, [Ollama](https://ollama.com/) con un modelo local que respete el esquema JSON, y [Hermes Agent](https://hermes-agent.nousresearch.com/docs/) sólo si se desea programación.
- Instalar dependencias y ejecutar pruebas: `python3 -m venv .venv && .venv/bin/python -m pip install -e '.[test]' && PYTHONPATH=src .venv/bin/python -m pytest -q tests`.
- Copiar `config/briefing.example.json` a `config/briefing.json` (excluido de Git), cambiar el tag de modelo por **uno instalado** y comprobarlo con `ollama list`.
- Validar sin enviar: `PYTHONPATH=src .venv/bin/python -m ai_daily_briefing.cli config/briefing.json`.
- Con Ollama y red disponibles, generar un reporte **sin enviar**: `PYTHONPATH=src .venv/bin/python scripts/run_once.py config/briefing.json --workdir var`. Verificar `var/artifacts/<id>/` y `var/audit.sqlite3`; `var/` está excluido de Git.

El JSON de ejemplo trae destinos inválidos y `send_enabled=false` a propósito. Ningún comando anterior manda correo ni crea un trabajo programado. Los reportes se redactan en español. Consulte [instalación y operación](docs/INSTALACION.es.md) antes de autorizar cualquier entrega.

## Límites

Las fuentes públicas y sus enlaces se verifican por accesibilidad, no por veracidad de todas sus afirmaciones. Para los papers de arXiv preseleccionados, la fecha original `published` de la API Atom —no la fecha de la entrada RSS— determina si entran en la ventana de 48 horas; el reporte distingue ambas fechas cuando el paper califica. Si no hay un paper elegible, esa categoría queda vacía aunque la entrada del feed sea reciente. Si faltan metadatos de arXiv o son inválidos, se cuenta un fallo de fuente y se bloquea el correo con el informe; una corrida autorizada aún puede publicar un estado de fallo en Slack. El modelo clasifica a partir de metadatos/resúmenes y puede equivocarse; las comprobaciones de puntuación y longitud no sustituyen la revisión editorial. Tavily queda opcional y apagado; Exa y Brave no están implementados. No se requieren ni se asumen créditos pagados. No hay garantía de puntualidad si el equipo duerme: la entrada programada acepta sólo los 15 minutos posteriores a la hora configurada y evita reintentos ciegos tras una salida incierta. Antes de activar cron hay que cotejar que la zona del programador coincida con la zona IANA del JSON; si no coincide, el reporte puede omitirse. Hermes puede interrumpir una corrida larga, por lo que el tiempo total con fuentes/modelo reales requiere medición en la máquina de destino.

La configuración local `.env`, `config/briefing.json`, `var/`, artefactos y registros quedan fuera del repositorio. **No copie datos privados del despliegue original** a esta copia. Se revisaron los archivos de esta copia para detectar patrones de credenciales y datos personales; esto no garantiza ausencia de todo riesgo. Revise los resúmenes frente a sus fuentes primarias antes de habilitar entregas.

## Licencia

[MIT](LICENSE). El horario del ejemplo es ilustrativo: configure su hora y zona antes de crear un trabajo.

English: [default README](README.md) · [Setup and safety guide](docs/SETUP.en.md).
