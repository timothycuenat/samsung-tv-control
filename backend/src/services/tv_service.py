import json
import os
import logging
import socket
from pathlib import Path
from .tv_control import TVControl
import asyncio
import time
from .config_service import ConfigService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TVService')

class SlideshowStateService:
    def __init__(self):
        self.slideshow_states = {}

    def set_state(self, ip_address: str, running: bool, duration: int, shuffle: bool, category: int):
        self.slideshow_states[ip_address] = {
            "running": running,
            "duration": duration,
            "shuffle": shuffle,
            "category": category
        }

    def get_state(self, ip_address: str) -> dict:
        return self.slideshow_states.get(ip_address, {
            "running": False,
            "duration": 0,
            "shuffle": False,
            "category": 0
        })

class TVService:
    def __init__(self):
        self.config_path = Path(__file__).parent.parent / 'config' / 'tvs.json'
        self.config_service = ConfigService()
        self.tokens_dir = Path(__file__).parent.parent / 'config' / 'tokens'
        self.tokens_dir.mkdir(exist_ok=True)
        self.load_config()
        self.tv_controls = {}  # Nouveau : {ip: TVControl}
        self.slideshow_state_service = SlideshowStateService()

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
            # Mise à jour de la config via ConfigService
            self.config_service.update_tv_status(ip_address, result["data"])
            duration = time.time() - start
            logger.info(f"[PERF] get_tv_status({ip_address}) - done in {duration:.3f}s")
            return result["data"]
        
        error_msg = result.get('error', 'Erreur inconnue')
        logger.error(f"Échec de la récupération de l'état de la TV {ip_address}: {error_msg}")
        duration = time.time() - start
        logger.info(f"[PERF] get_tv_status({ip_address}) - done in {duration:.3f}s")
        return {
            "error": error_msg,
            "error_type": "network_error" if "sous-réseau" in error_msg.lower() or "accessible" in error_msg.lower() else "unknown_error"
        }

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
            
        error_msg = result.get('error', 'Erreur inconnue')
        logger.error(f"Échec du contrôle de l'alimentation pour la TV {ip_address}: {error_msg}")
        duration = time.time() - start
        logger.info(f"[PERF] power_control({ip_address}, {action}) - done in {duration:.3f}s")
        return {
            "error": error_msg,
            "error_type": "network_error" if "sous-réseau" in error_msg.lower() or "accessible" in error_msg.lower() else "unknown_error"
        }

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

    async def upload_photo(self, ip_address, file_bytes, file_type="png", matte="none", portrait_matte="flexible_black"):
        tv_control = self.get_tv_control(ip_address)
        return await tv_control.upload_photo(file_bytes, file_type, matte, portrait_matte)

    async def list_art_images(self, ip_address):
        tv_control = self.get_tv_control(ip_address)
        return await tv_control.list_art_images()

    async def delete_art_images(self, ip_address, content_ids):
        tv_control = self.get_tv_control(ip_address)
        return await tv_control.delete_art_images(content_ids)

    async def set_auto_rotation(self, ip_address: str, duration: int, shuffle: bool, category: int) -> dict:
        """
        Configure la rotation automatique des images.
        
        Args:
            ip_address: Adresse IP de la TV
            duration: Durée en minutes (0 pour désactiver)
            shuffle: True pour aléatoire, False pour séquentiel
            category: 2=mes images, 4=favoris, 8=store
        """
        start = time.time()
        logger.info(f"[PERF] set_auto_rotation({ip_address}, duration={duration}, shuffle={shuffle}, category={category}) - start")
        
        tv_control = self.get_tv_control(ip_address)
        result = await tv_control.set_auto_rotation(duration, shuffle, category)
        
        if result.get("success", False):
            logger.info(f"Rotation automatique configurée avec succès pour la TV {ip_address}")
            duration = time.time() - start
            logger.info(f"[PERF] set_auto_rotation - done in {duration:.3f}s")
            return {"success": True, "data": result.get("data", {})}
        
        error_msg = result.get('error', 'Erreur inconnue')
        logger.error(f"Échec de la configuration de la rotation automatique pour la TV {ip_address}: {error_msg}")
        duration = time.time() - start
        logger.info(f"[PERF] set_auto_rotation - done in {duration:.3f}s")
        return {"success": False, "error": error_msg}

    async def get_auto_rotation_status(self, ip_address: str) -> dict:
        """
        Récupère le statut de la rotation automatique.
        
        Args:
            ip_address: Adresse IP de la TV
        """
        start = time.time()
        logger.info(f"[PERF] get_auto_rotation_status({ip_address}) - start")
        
        tv_control = self.get_tv_control(ip_address)
        result = await tv_control.get_auto_rotation_status()
        
        if result.get("success", False):
            logger.info(f"Statut de la rotation automatique récupéré avec succès pour la TV {ip_address}")
            duration = time.time() - start
            logger.info(f"[PERF] get_auto_rotation_status - done in {duration:.3f}s")
            return {"success": True, "data": result.get("data", {})}
        
        error_msg = result.get('error', 'Erreur inconnue')
        logger.error(f"Échec de la récupération du statut de la rotation automatique pour la TV {ip_address}: {error_msg}")
        duration = time.time() - start
        logger.info(f"[PERF] get_auto_rotation_status - done in {duration:.3f}s")
        return {"success": False, "error": error_msg}

    async def custom_slideshow(self, ip_address: str, duration: int, shuffle: bool, category: int) -> dict:
        """
        Gère le diaporama des images depuis le serveur.
        
        Args:
            ip_address: Adresse IP de la TV
            duration: Durée en secondes entre chaque image
            shuffle: True pour aléatoire, False pour séquentiel
            category: 2=mes images, 4=favoris, 8=store
        """
        start = time.time()
        logger.info(f"[PERF] custom_slideshow({ip_address}, duration={duration}, shuffle={shuffle}, category={category}) - start")
        
        tv_control = self.get_tv_control(ip_address)
        
        # Lancer le diaporama en arrière-plan
        asyncio.create_task(self._run_slideshow(tv_control, duration, shuffle, category))
        
        # Mettre à jour l'état du diaporama
        self.slideshow_state_service.set_state(ip_address, True, duration, shuffle, category)
        
        duration = time.time() - start
        logger.info(f"[PERF] custom_slideshow - done in {duration:.3f}s")
        return {"success": True, "message": "Diaporama démarré en arrière-plan"}

    async def _run_slideshow(self, tv_control: TVControl, duration: int, shuffle: bool, category: int):
        """
        Exécute le diaporama.
        """
        try:
            result = await tv_control.custom_slideshow(duration, shuffle, category)
            if not result.get("success", False):
                logger.error(f"Erreur lors de l'exécution du diaporama: {result.get('error', 'Erreur inconnue')}")
                self.slideshow_state_service.set_state(tv_control.ip_address, False, 0, False, 0)
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'exécution du diaporama: {str(e)}")
            self.slideshow_state_service.set_state(tv_control.ip_address, False, 0, False, 0)

    async def get_custom_slideshow_status(self, ip_address: str) -> dict:
        """
        Récupère l'état actuel du diaporama personnalisé.
        
        Args:
            ip_address: Adresse IP de la TV
        """
        return self.slideshow_state_service.get_state(ip_address)

    async def stop_custom_slideshow(self, ip_address: str):
        logger.info(f"Arrêt du diaporama pour la TV {ip_address}")
        self.slideshow_state_service.set_state(ip_address, False, 0, False, 0)
        # Annuler les tâches asynchrones en cours pour le diaporama
        tv_control = self.get_tv_control(ip_address)
        await tv_control.stop_slideshow_task()
        return {"success": True, "message": "Diaporama arrêté"} 