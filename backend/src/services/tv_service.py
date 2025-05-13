import json
import os
import logging
import socket
from pathlib import Path
from .tv_control import TVControl
import asyncio
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TVService')

class TVService:
    def __init__(self):
        self.config_path = Path(__file__).parent.parent / 'config' / 'tvs.json'
        self.tokens_dir = Path(__file__).parent.parent / 'config' / 'tokens'
        self.tokens_dir.mkdir(exist_ok=True)
        self.load_config()
        self.tv_controls = {}  # Nouveau : {ip: TVControl}

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

    def _get_token_file(self, ip_address: str) -> str:
        """Retourne le chemin du fichier de token pour une TV donnée"""
        return str(self.tokens_dir / f"token_{ip_address.replace('.', '_')}.txt")

    def get_tv_control(self, ip_address: str) -> TVControl:
        if ip_address not in self.tv_controls:
            token_file = self._get_token_file(ip_address)
            self.tv_controls[ip_address] = TVControl(ip_address, token_file=token_file)
        return self.tv_controls[ip_address]

    async def get_tv_status(self, ip_address: str) -> dict:
        start = time.time()
        logger.info(f"[PERF] get_tv_status({ip_address}) - start")
        logger.info(f"Récupération de l'état de la TV {ip_address}")
        tv_control = self.get_tv_control(ip_address)
        result = await tv_control.get_status()
        
        if result.get("success", False):
            logger.info(f"État de la TV {ip_address} récupéré avec succès")
            duration = time.time() - start
            logger.info(f"[PERF] get_tv_status({ip_address}) - done in {duration:.3f}s")
            return result["data"]
        
        logger.error(f"Échec de la récupération de l'état de la TV {ip_address}: {result.get('error')}")
        duration = time.time() - start
        logger.info(f"[PERF] get_tv_status({ip_address}) - done in {duration:.3f}s")
        return {"error": result.get("error")}

    async def power_control(self, ip_address, action: str):
        start = time.time()
        logger.info(f"[PERF] power_control({ip_address}, {action}) - start")
        logger.info(f"Tentative de contrôle de l'alimentation de la TV {ip_address} (action={action})")
        tv_control = self.get_tv_control(ip_address)
        result = await tv_control.power_control(action)
        
        if result["success"]:
            logger.info(f"Contrôle de l'alimentation réussi pour la TV {ip_address}")
            # On attend un peu pour laisser le temps à la TV de changer d'état
            await asyncio.sleep(3)
            # On récupère le nouveau statut
            status = await self.get_tv_status(ip_address)
            duration = time.time() - start
            logger.info(f"[PERF] power_control({ip_address}, {action}) - done in {duration:.3f}s")
            return {"success": True, "data": status}
            
        logger.error(f"Échec du contrôle de l'alimentation pour la TV {ip_address}: {result.get('error')}")
        duration = time.time() - start
        logger.info(f"[PERF] power_control({ip_address}, {action}) - done in {duration:.3f}s")
        return {"error": result["error"]}

    async def set_art_mode(self, ip_address, action: str):
        start = time.time()
        logger.info(f"[PERF] set_art_mode({ip_address}, {action}) - start")
        logger.info(f"Tentative de contrôle du mode Art pour la TV {ip_address} (action={action})")
        tv_control = self.get_tv_control(ip_address)
        
        result = await tv_control.art_mode_control(action)
        if not result["success"]:
            return {"error": result["error"]}
        # On récupère le nouveau statut complet pour la réponse API
        status = await self.get_tv_status(ip_address)
        duration = time.time() - start
        logger.info(f"[PERF] set_art_mode({ip_address}, {action}) - done in {duration:.3f}s")
        return {"success": True, "data": status}

    async def close_all(self):
        start = time.time()
        logger.info(f"[PERF] close_all - start")
        logger.info("Fermeture de toutes les connexions aux TVs")
        awaitables = []
        for ip, tv_control in self.tv_controls.items():
            try:
                awaitables.append(tv_control.close())
                logger.info(f"Connexion fermée pour la TV {ip}")
            except Exception as e:
                logger.error(f"Erreur lors de la fermeture de la connexion pour la TV {ip}: {e}")
        await asyncio.gather(*awaitables, return_exceptions=True)
        self.tv_controls.clear()
        duration = time.time() - start
        logger.info(f"[PERF] close_all - done in {duration:.3f}s")

    async def upload_photo(self, ip_address, file_bytes, file_type="png", matte="shadowbox_polar", portrait_matte="shadowbox_polar"):
        tv_control = self.get_tv_control(ip_address)
        return await tv_control.upload_photo(file_bytes, file_type, matte, portrait_matte)

    async def list_art_images(self, ip_address):
        tv_control = self.get_tv_control(ip_address)
        return await tv_control.list_art_images()

    async def delete_art_images(self, ip_address, content_ids):
        tv_control = self.get_tv_control(ip_address)
        return await tv_control.delete_art_images(content_ids) 