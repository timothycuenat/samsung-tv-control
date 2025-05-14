import json
from pathlib import Path
import logging

logger = logging.getLogger('ConfigService')

class ConfigService:
    def __init__(self, config_path=None):
        if config_path is None:
            self.config_path = Path(__file__).parent.parent / 'config' / 'tvs.json'
        else:
            self.config_path = Path(config_path)
        self.load_config()

    def load_config(self):
        if not self.config_path.exists():
            logger.info("Création du fichier de configuration")
            self.tvs = {"tvs": []}
            self.save_config()
        else:
            logger.info("Chargement de la configuration")
            with open(self.config_path, 'r') as f:
                self.tvs = json.load(f)

    def save_config(self):
        logger.info("Sauvegarde de la configuration")
        with open(self.config_path, 'w') as f:
            json.dump(self.tvs, f, indent=4)

    def get_tvs(self):
        return self.tvs["tvs"]

    def update_tv_status(self, ip_address, status):
        """Met à jour le nom et le modelName d'une TV identifiée par son IP, à partir de status['raw_device_info']['device']."""
        device_info = status.get("raw_device_info", {}).get("device", {})
        name = device_info.get("name")
        model_name = device_info.get("modelName")
        for tv in self.tvs["tvs"]:
            if tv.get("ip") == ip_address:
                if name:
                    tv["name"] = name
                if model_name:
                    tv["modelName"] = model_name
                self.save_config()
                return True
        return False 