import json
import logging
import asyncio
import socket
from typing import Optional, Dict, Any
from pathlib import Path
from lib.samsungtvws.async_remote import SamsungTVWSAsyncRemote
from lib.samsungtvws.rest import SamsungTVRest
from lib.samsungtvws.remote import SendRemoteKey
from lib.samsungtvws.async_art import SamsungTVAsyncArt
import time
import random

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TVControl')

class TVControl:
    _slideshow_task = None  # Singleton pour la tâche de diaporama

    def __init__(self, ip_address: str, port: int = 8002, token_file: Optional[str] = None):
        self.ip_address = ip_address
        self.port = port
        self.tv: Optional[SamsungTVWSAsyncRemote] = None
        self.tv_rest: Optional[SamsungTVRest] = None
        self.tv_art: Optional[SamsungTVAsyncArt] = None
        if token_file is None:
            token_file = Path(__file__).parent.parent / 'config' / f'token_{ip_address.replace(".", "_")}.txt'
        self.token_file = str(token_file)
        self._stop_slideshow = False  # Flag pour arrêter le diaporama
        self.slideshow_task = None  # Tâche de diaporama

    def _check_network_connectivity(self) -> tuple[bool, str]:
        """
        Vérifie la connectivité réseau avec la TV.
        Retourne un tuple (succès, message_erreur)
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.ip_address, self.port))
            sock.close()
            
            if result == 0:
                return True, "Connexion réseau établie"
            
            if result == 113:  # No route to host
                return False, f"La TV n'est pas accessible sur le réseau actuel. Vérifiez que vous êtes sur le même sous-réseau que la TV ({self.ip_address})"
            
            if result == 111:  # Connection refused
                return False, f"La TV refuse la connexion sur {self.ip_address}:{self.port}. Vérifiez que la TV est allumée et que le service est actif."
            
            if result == 110:  # Connection timed out
                return False, f"La connexion à la TV a expiré ({self.ip_address}:{self.port}). Vérifiez que la TV est allumée et accessible."
            
            return False, f"Impossible d'atteindre la TV sur {self.ip_address}:{self.port} (code erreur: {result})"
        except Exception as e:
            return False, f"Erreur lors de la connexion à la TV: {str(e)}"

    async def connect(self) -> tuple[bool, str]:
        start = time.time()
        logger.info(f"[PERF] TVControl.connect({self.ip_address}) - start")
        try:
            logger.info(f"Tentative de connexion à la TV {self.ip_address}:{self.port}")
            
            # Vérification de la connectivité réseau
            success, error_msg = self._check_network_connectivity()
            if not success:
                logger.error(error_msg)
                duration = time.time() - start
                logger.info(f"[PERF] TVControl.connect({self.ip_address}) - done in {duration:.3f}s (FAILED)")
                return False, error_msg
            
            # Créer l'instance pour les commandes
            self.tv = SamsungTVWSAsyncRemote(
                host=self.ip_address,
                port=self.port,
                token_file=self.token_file,
                name="Samsung TV Controller"
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
            
            # On attend un peu pour s'assurer que la connexion est bien établie
            logger.info("Connexion établie avec succès")
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.connect({self.ip_address}) - done in {duration:.3f}s")
            return True, ""
        except Exception as e:
            error_msg = str(e)
            if "No route to host" in error_msg or "Network is unreachable" in error_msg:
                error_msg = f"La TV n'est pas accessible sur le réseau actuel. Vérifiez que vous êtes sur le même sous-réseau que la TV ({self.ip_address})"
            elif "ms.channel.timeOut" in error_msg:
                error_msg = f"La TV Samsung a rejeté la connexion. Les TV Samsung exigent d'être sur exactement le même sous-réseau (même si un ping fonctionne). Vérifiez que votre appareil est sur le même sous-réseau que la TV ({self.ip_address})"
            logger.error(f"Erreur lors de la connexion: {error_msg}")
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.connect({self.ip_address}) - done in {duration:.3f}s (FAILED)")
            return False, error_msg

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

    async def ensure_connected(self) -> tuple[bool, str]:
        if not self.tv or not self.tv_rest or not self.tv_art:
            return await self.connect()
        return True, ""

    async def get_status(self) -> Dict[str, Any]:
        start = time.time()
        logger.info(f"[PERF] TVControl.get_status({self.ip_address}) - start")
        success, error_msg = await self.ensure_connected()
        if not success:
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.get_status({self.ip_address}) - done in {duration:.3f}s (FAILED)")
            return {
                "success": False, 
                "error": error_msg,
                "error_type": "network_error" if "sous-réseau" in error_msg.lower() or "accessible" in error_msg.lower() else "connection_error"
            }

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
            error_msg = str(e)
            if "No route to host" in error_msg or "Network is unreachable" in error_msg:
                error_msg = f"La TV n'est pas accessible sur le réseau actuel. Vérifiez que vous êtes sur le même sous-réseau que la TV ({self.ip_address})"
            elif "ms.channel.timeOut" in error_msg:
                error_msg = f"La TV Samsung a rejeté la connexion. Les TV Samsung exigent d'être sur exactement le même sous-réseau (même si un ping fonctionne). Vérifiez que votre appareil est sur le même sous-réseau que la TV ({self.ip_address})"
            logger.error(f"Erreur lors de la récupération de l'état: {error_msg}")
            duration = time.time() - start
            logger.info(f"[PERF] TVControl.get_status({self.ip_address}) - done in {duration:.3f}s (FAILED)")
            return {
                "success": False, 
                "error": error_msg,
                "error_type": "network_error" if "sous-réseau" in error_msg.lower() or "accessible" in error_msg.lower() else "connection_error"
            }

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

    async def upload_photo(self, file_bytes, file_type="png", matte="", portrait_matte="flexible_black"):
        await self.ensure_connected()
        if not self.tv_art:
            return {"success": False, "error": "Impossible de se connecter au canal Art"}
        try:
            # On fait l'upload de manière asynchrone
            upload_task = asyncio.create_task(self.tv_art.upload(
                file=file_bytes,
                matte=matte,
                portrait_matte=portrait_matte,
                file_type=file_type
            ))
            
            # On vérifie que l'image a bien été uploadée avec un polling
            max_attempts = 5
            attempt = 0
            while attempt < max_attempts:
                # On vérifie d'abord si l'upload est terminé
                if upload_task.done():
                    try:
                        await upload_task  # On attend la fin de l'upload si ce n'est pas déjà fait
                    except Exception as e:
                        return {"success": False, "error": f"Erreur lors de l'upload: {str(e)}"}
                
                images_result = await self.list_art_images()
                if not images_result.get("success"):
                    return {"success": False, "error": "Impossible de vérifier l'upload"}
                    
                images = images_result.get("images", [])
                if images:
                    # On trie les images par date pour avoir la plus récente
                    latest_image = max(images, key=lambda x: x.get('image_date', ''))
                    return {
                        "success": True,
                        "content_id": latest_image.get('content_id'),
                        "image_details": latest_image
                    }
                
                attempt += 1
                if attempt < max_attempts:
                    await asyncio.sleep(0.5)  # Attente courte entre les tentatives
            
            return {"success": False, "error": "L'image n'a pas été trouvée après l'upload"}
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
        try:
            if not content_ids:
                return {"success": False, "error": "Aucun ID d'image spécifié"}
            
            if isinstance(content_ids, str):
                content_ids = [content_ids]
            
            result = await self.tv_art.delete_list(content_ids)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_auto_rotation(self, duration: int, shuffle: bool, category: int) -> dict:
        """
        Configure la rotation automatique des images.
        
        Args:
            duration: Durée en minutes (0 pour désactiver)
            shuffle: True pour aléatoire, False pour séquentiel
            category: 2=mes images, 4=favoris, 8=store
        """
        try:
            result = await self.tv_art.set_auto_rotation_status(duration, shuffle, category)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_slideshow(self, duration: int, shuffle: bool, category: int) -> dict:
        """
        Configure le diaporama des images.
        
        Args:
            duration: Durée en minutes (0 pour désactiver)
            shuffle: True pour aléatoire, False pour séquentiel
            category: 2=mes images, 4=favoris, 8=store
        """
        try:
            await self.ensure_connected()
            if not self.tv_art:
                return {"success": False, "error": "Impossible de se connecter au canal Art"}
            
            # Vérifier si le mode Art est supporté
            if not await self.tv_art.supported():
                return {"success": False, "error": "Le mode Art n'est pas supporté par cette TV"}
            
            # Vérifier si le mode Art est activé
            art_mode = await self.tv_art.get_artmode()
            if art_mode != "on":
                return {"success": False, "error": "Le mode Art n'est pas activé. Activez d'abord le mode Art."}
            
            # Vérifier si la catégorie existe
            available_categories = await self.tv_art.available(category=f"MY-C000{category}")
            if not available_categories:
                return {"success": False, "error": f"Aucune image trouvée dans la catégorie {category}"}
            
            # S'assurer que la durée est valide
            if duration < 0:
                return {"success": False, "error": "La durée doit être un nombre positif"}
            
            # Vérifier le statut actuel
            current_status = await self.tv_art.get_auto_rotation_status()
            logger.info(f"Statut actuel de la rotation : {current_status}")
            
            # Utiliser set_auto_rotation_status avec l'événement de confirmation
            data = await self.tv_art._send_art_request(
                {
                    "request": "set_auto_rotation_status",
                    "value": str(duration) if duration > 0 else "off",
                    "category_id": f"MY-C000{category}",
                    "type": "shuffleslideshow" if shuffle else "slideshow"
                },
                wait_for_event="auto_rotation_changed"
            )
            
            if not data:
                return {"success": False, "error": "La TV n'a pas confirmé le changement"}
            
            logger.info(f"Résultat de la configuration : {data}")
            
            # Vérifier le nouveau statut
            new_status = await self.tv_art.get_auto_rotation_status()
            logger.info(f"Nouveau statut de la rotation : {new_status}")
            
            return {"success": True, "data": new_status}
        except Exception as e:
            logger.error(f"Erreur lors de la configuration du diaporama : {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_auto_rotation_status(self) -> dict:
        """
        Récupère le statut de la rotation automatique.
        """
        try:
            result = await self.tv_art.get_auto_rotation_status()
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_slideshow_status(self) -> dict:
        """
        Récupère le statut du diaporama.
        """
        try:
            await self.ensure_connected()
            if not self.tv_art:
                return {"success": False, "error": "Impossible de se connecter au canal Art"}
            
            # Vérifier si le mode Art est supporté
            if not await self.tv_art.supported():
                return {"success": False, "error": "Le mode Art n'est pas supporté par cette TV"}
            
            # Vérifier si le mode Art est activé
            art_mode = await self.tv_art.get_artmode()
            if art_mode != "on":
                return {"success": False, "error": "Le mode Art n'est pas activé"}
            
            result = await self.tv_art.get_slideshow_status()
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _check_art_mode_support(self) -> bool:
        """
        Vérifie si le mode art est supporté par la TV.
        """
        try:
            await self.ensure_connected()
            if not self.tv_art:
                return False
            
            return await self.tv_art.supported()
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du support du mode art: {str(e)}")
            return False

    async def custom_slideshow(self, duration: int, shuffle: bool, category: int) -> dict:
        """
        Démarre un diaporama personnalisé avec les images de la catégorie spécifiée.
        
        Args:
            duration: Durée en secondes entre chaque image
            shuffle: True pour mélanger les images, False pour l'ordre séquentiel
            category: 2=mes images, 4=favoris, 8=store
        """
        try:
            await self.ensure_connected()
            if not self.tv_art:
                return {"success": False, "error": "Impossible de se connecter au canal Art"}

            # Vérifier si le mode art est supporté
            if not await self.tv_art.supported():
                return {"success": False, "error": "Le mode art n'est pas supporté sur cette TV"}

            # Vérifier si le mode art est activé
            status = await self.get_status()
            if not status.get("success", False):
                return {"success": False, "error": "Impossible de vérifier l'état du mode art"}
            
            if not status.get("data", {}).get("art_mode", False):
                # Activer le mode art si nécessaire
                logger.info("Mode art non activé, tentative d'activation...")
                result = await self.art_mode_control("on")
                if not result.get("success", False):
                    return {"success": False, "error": "Impossible d'activer le mode art"}
                
                # Attendre que le mode art soit activé
                for _ in range(10):  # 10 tentatives de 2 secondes
                    await asyncio.sleep(2)
                    status = await self.get_status()
                    if status.get("success", False) and status.get("data", {}).get("art_mode", False):
                        logger.info("Mode art activé avec succès")
                        break
                else:
                    return {"success": False, "error": "Le mode art n'a pas pu être activé"}

            # Récupérer la liste des images
            logger.info("Récupération des images...")
            images_result = await self.list_art_images()
            if not images_result.get("success", False):
                return {"success": False, "error": "Impossible de récupérer la liste des images"}
            
            images = images_result.get("images", [])
            if not images:
                return {"success": False, "error": "Aucune image trouvée dans la catégorie spécifiée"}
            
            logger.info(f"Nombre d'images trouvées : {len(images)}")
            
            # Mélanger les images si demandé
            if shuffle:
                logger.info("Images mélangées")
                random.shuffle(images)
            
            # Annuler la tâche existante si elle existe
            if self.slideshow_task and not self.slideshow_task.done():
                self.slideshow_task.cancel()
                try:
                    await self.slideshow_task
                except asyncio.CancelledError:
                    pass
            
            # Créer et démarrer la nouvelle tâche
            self.slideshow_task = asyncio.create_task(self._run_slideshow_loop(images, duration))
            logger.info("Tâche de diaporama créée et démarrée")
            
            return {"success": True, "message": "Diaporama démarré"}
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du diaporama: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _run_slideshow_loop(self, images: list, duration: int):
        """
        Exécute le diaporama en boucle continue.
        """
        try:
            logger.info("Démarrage de la tâche de diaporama...")
            self._stop_slideshow = False  # Réinitialiser le flag au démarrage
            while not self._stop_slideshow:  # Vérifier le flag d'arrêt
                for i, image in enumerate(images, 1):
                    if self._stop_slideshow:  # Vérifier le flag d'arrêt
                        logger.info("Diaporama arrêté explicitement")
                        return

                    # Vérifier si le mode art est toujours actif
                    status = await self.get_status()
                    if not status.get("success", False) or not status.get("data", {}).get("art_mode", False):
                        logger.info("Mode art désactivé, arrêt du diaporama")
                        return
                    
                    # Afficher l'image
                    logger.info(f"Affichage de l'image {i}/{len(images)} (ID: {image['content_id']})")
                    try:
                        await self.tv_art.select_image(image['content_id'])
                        logger.info(f"Image {image['content_id']} affichée avec succès")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'affichage de l'image {image['content_id']}: {str(e)}")
                        continue
                    
                    # Attendre la durée spécifiée
                    logger.info(f"Attente de {duration} secondes avant la prochaine image...")
                    await asyncio.sleep(duration)
                
                logger.info("Fin du cycle, redémarrage du diaporama...")
                
        except asyncio.CancelledError:
            logger.info("Tâche de diaporama annulée")
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue dans la tâche de diaporama: {str(e)}")
            raise
        finally:
            self._stop_slideshow = False  # Réinitialiser le flag à la fin

    async def stop_slideshow_task(self):
        """
        Arrête le diaporama en cours.
        """
        logger.info(f"Arrêt du diaporama pour la TV {self.ip_address}")
        self._stop_slideshow = True  # Activer le flag d'arrêt
        
        # Annuler la tâche si elle existe
        if self.slideshow_task and not self.slideshow_task.done():
            self.slideshow_task.cancel()
            try:
                await self.slideshow_task
            except asyncio.CancelledError:
                pass
            finally:
                self.slideshow_task = None  # Réinitialiser la référence à la tâche
                self._stop_slideshow = False  # Réinitialiser le flag d'arrêt 