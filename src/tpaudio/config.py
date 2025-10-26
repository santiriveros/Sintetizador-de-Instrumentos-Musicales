import yaml
import os

def load_presets(instruments_path: str, effects_path: str = None):
    """
    Carga los archivos YAML de presets de instrumentos y efectos.
    Si las rutas son relativas, las convierte a absolutas desde el directorio raíz del proyecto.
    """
    presets = {}

    def _load_yaml(path):
        if not path:
            return {}
        full = os.path.abspath(path)
        if not os.path.exists(full):
            print(f"[WARN] No se encontró el archivo de presets: {full}")
            return {}
        with open(full, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    print(f"[WARN] El YAML no tiene formato dict: {full}")
                    return {}
                return data
            except yaml.YAMLError as e:
                print(f"[ERR] Error leyendo YAML {full}: {e}")
                return {}

    instruments = _load_yaml(instruments_path)
    effects = _load_yaml(effects_path)
    presets.update(instruments or {})
    presets["effects"] = effects or {}
    print(f"[OK] Presets cargados correctamente desde: {os.path.abspath(instruments_path)}")
    return presets
