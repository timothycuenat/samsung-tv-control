import json
import logging
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from lib.samsungtvws.async_remote import SamsungTVWSAsyncRemote
from lib.samsungtvws.rest import SamsungTVRest
from lib.samsungtvws.remote import SendRemoteKey
from lib.samsungtvws.async_art import SamsungTVAsyncArt
import time

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TVControl')

class TVControl:
    def __init__(self, ip_address: str, port: int = 8002, token_file: Optional[str] = None):
        self.ip_address = ip_address
        self.port = port
        self.tv: Optional[SamsungTVWSAsyncRemote] = None
        self.tv_rest: Optional[SamsungTVRest] = None
        self.tv_art: Optional[SamsungTVAsyncArt] = None
        if token_file is None:
            token_file = Path(__file__).parent.parent / 'config' / f'token_{ip_address.replace(".", "_")}.txt'
        self.token_file = str(token_file)

    async def connect(self) -> bool:
        start = time.time()
        logger.info(f"[PERF] TVControl.connect({self.ip_address}) - start")
        try:
            logger.info(f"Tentative de connexion à la TV {self.ip_address}:{self.port}")
            
            # Créer l'instance pour les commandes
            self.tv = SamsungTVWSAsyncRemote(
                host=self.ip_address,
                port=self.port,
                token_file=self.token_file
            )
            await self.tv.start_listening()
            
            # Créer l'instance pour l'état
            self.tv_rest = SamsungTVRest(
                host=self.ip_address,
                port=8001  # Port REST différent
            )
            
            # Créer l'instance pour le mode art
            self.tv_art = SamsungTVAsyncArt(
                host=self.ip_address,
                token_file=self.token_file,
                port=self.port
            )
            await self.tv_art.start_listening()
            # Test explicite du canal Art
            logger.info("Test explicite du canal Art : appel à get_artmode() avec timeout court...")
            try:
                import asyncio
                artmode_status = await asyncio.wait_for(self.tv_art.get_artmode(), timeout=1)
                logger.info(f"Réponse explicite get_artmode() : {artmode_status}")
            except Exception as e:
                logger.warning(f"Erreur explicite get_artmode() : {e}")
            logger.info("Fin du test explicite du canal Art.")
            
            # On attend un peu pour s'assurer que la connexion est bien établie
            logger.info("Connexion établie avec succès")
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.connect({self.ip_address}) - done in {duration:.3f}s")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la connexion: {e}")
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.connect({self.ip_address}) - done in {duration:.3f}s (FAILED)")
            return False

    async def disconnect(self):
        if self.tv:
            try:
                await self.tv.close()
                logger.info("Déconnexion réussie")
            except Exception as e:
                logger.error(f"Erreur lors de la déconnexion: {e}")
        if self.tv_art:
            try:
                await self.tv_art.close()
                logger.info("Déconnexion du mode art réussie")
            except Exception as e:
                logger.error(f"Erreur lors de la déconnexion du mode art: {e}")

    async def ensure_connected(self):
        if not self.tv or not self.tv_rest or not self.tv_art:
            await self.connect()

    async def get_status(self) -> Dict[str, Any]:
        start = time.time()
        logger.info(f"[PERF] TVControl.get_status({self.ip_address}) - start")
        await self.ensure_connected()
        if not self.tv or not self.tv_rest or not self.tv_art:
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.get_status({self.ip_address}) - done in {duration:.3f}s (FAILED)")
            return {"success": False, "error": "Impossible de se connecter à la TV"}

        try:
            # Récupération des informations détaillées de la TV
            device_info = self.tv_rest.rest_device_info()
            
            # État de la TV (allumée/éteinte)
            tv_on = device_info.get('device', {}).get('PowerState', 'off') == 'on'
            
            # Détection simple du mode art
            art_mode = False
            try:
                await self.tv_art.start_listening()
                if await self.tv_art.supported():
                    art_mode = (await self.tv_art.get_artmode()) == "on"
                    logger.info(f"art_mode: {art_mode}")
            except Exception as e:
                logger.warning(f"Erreur lors de la détection du mode art: {e}")

            duration = time.time() - start
            logger.info(f"[PERF] TVControl.get_status({self.ip_address}) - done in {duration:.3f}s")
            return {
                "success": True,
                "data": {
                    "tv_on": tv_on,
                    "art_mode": art_mode,
                    "raw_device_info": device_info
                }
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'état: {e}")
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.get_status({self.ip_address}) - done in {duration:.3f}s (FAILED)")
            return {"success": False, "error": str(e)}

    async def send_command(self, key: str) -> Dict[str, Any]:
        await self.ensure_connected()
        if not self.tv:
            return {"success": False, "error": "Impossible de se connecter à la TV"}
        try:
            logger.info(f"Envoi de la commande {key}")
            await self.tv.send_command(SendRemoteKey.click(key))
            return {"success": True, "message": f"Commande {key} envoyée avec succès"}
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la commande: {e}")
            return {"success": False, "error": str(e)}

    async def power_control(self, action: str = "toggle"):
        start = time.time()
        logger.info(f"[PERF] TVControl.power_control({self.ip_address}, {action}) - start")
        await self.ensure_connected()
        if not self.tv or not self.tv_rest:
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.power_control({self.ip_address}, {action}) - done in {duration:.3f}s (FAILED)")
            return {"success": False, "error": "Impossible de se connecter à la TV"}
        try:
            # On récupère l'état actuel de la TV
            tv_on = self.tv_rest.rest_power_state()
            logger.info(f"État actuel de la TV (valeur brute): {tv_on}")
            logger.info(f"État actuel de la TV: {'allumée' if tv_on else 'éteinte'}")
            
            # On détermine si on doit envoyer une commande
            should_send_command = False
            
            if action == "on":
                if not tv_on:
                    should_send_command = True
                    logger.info("Mode ON : la TV est éteinte, on l'allume")
                else:
                    logger.info("Mode ON : la TV est déjà allumée, pas besoin d'envoyer de commande")
            elif action == "off":
                if tv_on:
                    should_send_command = True
                    logger.info("Mode OFF : la TV est allumée, on l'éteint")
                else:
                    logger.info("Mode OFF : la TV est déjà éteinte, pas besoin d'envoyer de commande")
            else:  # toggle
                should_send_command = True
                logger.info("Mode toggle : on envoie toujours la commande")
            
            # Si on doit envoyer une commande
            if should_send_command:
                logger.info("Envoi de la commande power (hold 3s)...")
                await self.tv.send_command(SendRemoteKey.hold("KEY_POWER", seconds=3))
                # Récupérer le nouvel état
                tv_on = self.tv_rest.rest_power_state()
                logger.info(f"Nouvel état de la TV (valeur brute): {tv_on}")
                logger.info(f"Nouvel état de la TV: {'allumée' if tv_on else 'éteinte'}")
            
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.power_control({self.ip_address}, {action}) - done in {duration:.3f}s")
            return {
                "success": True,
                "data": {
                    "tv_on": tv_on
                }
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la commande power: {e}")
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.power_control({self.ip_address}, {action}) - done in {duration:.3f}s (FAILED)")
            return {"success": False, "error": str(e)}

    async def art_mode_control(self, action: str = "toggle"):
        """
        Contrôle le mode art de la TV (toggle, on, off)
        """
        start = time.time()
        logger.info(f"[PERF] TVControl.art_mode_control({self.ip_address}, {action}) - start")
        await self.ensure_connected()
        if not self.tv:
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.art_mode_control({self.ip_address}, {action}) - done in {duration:.3f}s (FAILED)")
            return {"success": False, "error": "Impossible de se connecter à la TV"}
        try:
            # On récupère l'état actuel du mode art
            art_mode = False
            try:
                if self.tv_art and await self.tv_art.supported():
                    art_mode = (await self.tv_art.get_artmode()) == "on"
            except Exception as e:
                logger.warning(f"Erreur lors de la détection du mode art: {e}")

            should_send_command = False
            logger.info(f"État détecté du mode art avant action '{action}': {art_mode}")
            if action == "on":
                if not art_mode:
                    should_send_command = True
                    logger.info("Mode art ON : il est désactivé, on l'active")
                else:
                    logger.info("Mode art ON : il est déjà activé, pas besoin d'envoyer de commande")
            elif action == "off":
                if art_mode:
                    should_send_command = True
                    logger.info("Mode art OFF : il est activé, on le désactive")
                else:
                    logger.info("Mode art OFF : il est déjà désactivé, pas besoin d'envoyer de commande")
            else:  # toggle
                should_send_command = True
                logger.info("Mode art TOGGLE : on envoie toujours la commande")

            if should_send_command:
                logger.info("Envoi de la commande KEY_POWER pour le mode art...")
                await self.tv.send_command(SendRemoteKey.click("KEY_POWER"))
                # On récupère le nouvel état
                art_mode = False
                try:
                    if self.tv_art and await self.tv_art.supported():
                        art_mode = (await self.tv_art.get_artmode()) == "on"
                except Exception as e:
                    logger.warning(f"Erreur lors de la détection du mode art après commande: {e}")
                duration = time.time() - start
                logger.info(f"[PERF] TVControl.art_mode_control({self.ip_address}, {action}) - done in {duration:.3f}s")
                return {"success": True, "art_mode": art_mode}
            else:
                duration = time.time() - start
                logger.info(f"[PERF] TVControl.art_mode_control({self.ip_address}, {action}) - done in {duration:.3f}s")
                return {"success": True, "art_mode": art_mode}
        except Exception as e:
            logger.error(f"Erreur lors du contrôle du mode art: {e}")
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.art_mode_control({self.ip_address}, {action}) - done in {duration:.3f}s (FAILED)")
            return {"success": False, "error": str(e)}

    async def set_volume(self, volume: int):
        if not 0 <= volume <= 100:
            return {"success": False, "error": "Le volume doit être entre 0 et 100"}
        
        try:
            # Envoyer la commande de volume
            if volume == 0:
                return await self.send_command("KEY_MUTE")
            else:
                return await self.send_command("KEY_VOLUP")
        except Exception as e:
            logger.error(f"Erreur lors du réglage du volume: {e}")
            return {"success": False, "error": str(e)}

    async def set_channel(self, channel: int):
        try:
            # Convertir le numéro de chaîne en séquence de touches
            channel_str = str(channel)
            result = {"success": True, "message": "Chaîne changée avec succès"}
            
            for digit in channel_str:
                cmd_result = await self.send_command(f"KEY_{digit}")
                if not cmd_result["success"]:
                    return cmd_result
            
            # Confirmer avec ENTER
            return await self.send_command("KEY_ENTER")
        except Exception as e:
            logger.error(f"Erreur lors du changement de chaîne: {e}")
            return {"success": False, "error": str(e)}

    async def power_on(self):
        return await self.send_command("KEY_POWERON")

    async def power_off(self):
        return await self.send_command("KEY_POWEROFF")

    async def mute(self):
        return await self.send_command("KEY_MUTE")

    async def channel_up(self):
        return await self.send_command("KEY_CHANNELUP")

    async def channel_down(self):
        return await self.send_command("KEY_CHANNELDOWN")

    async def open_app(self, app_id: str):
        return await self.send_command(f"KEY_APP_{app_id}")

    async def home(self):
        return await self.send_command("KEY_HOME")

    async def menu(self):
        return await self.send_command("KEY_MENU")

    async def back(self):
        return await self.send_command("KEY_RETURN")

    async def up(self):
        return await self.send_command("KEY_UP")

    async def down(self):
        return await self.send_command("KEY_DOWN")

    async def left(self):
        return await self.send_command("KEY_LEFT")

    async def right(self):
        return await self.send_command("KEY_RIGHT")

    async def enter(self):
        return await self.send_command("KEY_ENTER")

    async def close(self):
        """Ferme proprement la connexion à la TV"""
        start = time.time()
        logger.info(f"[PERF] TVControl.close({self.ip_address}) - start")
        if self.tv:
            try:
                await self.tv.close()
                self.tv = None
                self.tv_rest = None
                logger.info("Connexion fermée avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de la fermeture de la connexion: {e}")
        duration = time.time() - start
        logger.info(f"[PERF] TVControl.close({self.ip_address}) - done in {duration:.3f}s")

    async def upload_photo(self, file_bytes, file_type="png", matte="shadowbox_polar", portrait_matte="shadowbox_polar"):
        await self.ensure_connected()
        if not self.tv_art:
            return {"success": False, "error": "Impossible de se connecter au canal Art"}
        try:
            content_id = await self.tv_art.upload(
                file=file_bytes,
                matte=matte,
                portrait_matte=portrait_matte,
                file_type=file_type
            )
            if content_id:
                return {"success": True, "content_id": content_id}
            else:
                return {"success": False, "error": "Upload échoué"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_art_images(self):
        import logging
        logger = logging.getLogger("TVControl.list_art_images")
        await self.ensure_connected()
        if not self.tv_art:
            logger.error("Impossible de se connecter au canal Art")
            return {"success": False, "error": "Impossible de se connecter au canal Art"}
        try:
            logger.info("Démarrage de start_listening sur le canal Art...")
            await self.tv_art.start_listening()
            logger.info("Vérification du support du canal Art...")
            supported = await self.tv_art.supported()
            logger.info(f"Canal Art supporté : {supported}")
            if not supported:
                return {"success": False, "error": "Le canal Art n'est pas supporté ou la TV n'est pas en mode Art"}
            logger.info("Appel à available(category='MY-C0002') pour lister les images personnelles...")
            images = await self.tv_art.available(category='MY-C0002')
            logger.info(f"Images récupérées : {images}")
            return {"success": True, "images": images}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des images Art Mode : {e}")
            return {"success": False, "error": str(e)}

    async def delete_art_images(self, content_ids):
        import logging
        logger = logging.getLogger("TVControl.delete_art_images")
        await self.ensure_connected()
        if not self.tv_art:
            logger.error("Impossible de se connecter au canal Art")
            return {"success": False, "error": "Impossible de se connecter au canal Art"}
        try:
            logger.info(f"Suppression des images : {content_ids}")
            await self.tv_art.delete_list(content_ids)
            logger.info("Suppression effectuée.")
            return {"success": True}
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des images Art Mode : {e}")
            return {"success": False, "error": str(e)} 