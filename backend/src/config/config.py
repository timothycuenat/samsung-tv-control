import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
import asyncio
import aiohttp
import platform

class TVConfig(BaseModel):
    name: str
    ip_address: str
    mac_address: str
    model: Optional[str] = None
    token: Optional[str] = None
    is_online: bool = False
    last_seen: Optional[datetime] = None

class Config:
    def __init__(self):
        self.config_dir = Path("config")
        self.config_file = self.config_dir / "tvs.json"
        self.config_dir.mkdir(exist_ok=True)
        self._ensure_config_file()
        self.tvs: Dict[str, TVConfig] = self._load_config()

    def _ensure_config_file(self):
        if not self.config_file.exists():
            with open(self.config_file, "w") as f:
                json.dump({}, f)

    def _load_config(self) -> Dict[str, TVConfig]:
        with open(self.config_file, "r") as f:
            data = json.load(f)
            return {
                ip: TVConfig(**tv_data)
                for ip, tv_data in data.items()
            }

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(
                {
                    ip: tv.dict()
                    for ip, tv in self.tvs.items()
                },
                f,
                indent=2,
                default=str
            )

    async def _ping(self, ip: str) -> bool:
        """
        Vérifie si une adresse IP est accessible via ping
        """
        try:
            if platform.system().lower() == "windows":
                # Windows
                proc = await asyncio.create_subprocess_shell(
                    f"ping -n 1 -w 1000 {ip}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                # Unix/Linux/MacOS
                proc = await asyncio.create_subprocess_shell(
                    f"ping -c 1 -W 1 {ip}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await proc.communicate()
            return proc.returncode == 0
        except Exception as e:
            print(f"Erreur lors du ping de {ip}: {e}")
            return False

    async def check_tvs_availability(self):
        """
        Vérifie la disponibilité de toutes les TVs configurées
        """
        for ip, tv in self.tvs.items():
            is_online = await self._ping(ip)
            if tv.is_online != is_online:
                self.update_tv(ip, {
                    "is_online": is_online,
                    "last_seen": datetime.now() if is_online else tv.last_seen
                })

    def add_tv(self, tv: TVConfig):
        self.tvs[tv.ip_address] = tv
        self.save_config()

    def remove_tv(self, ip_address: str):
        if ip_address in self.tvs:
            del self.tvs[ip_address]
            self.save_config()

    def get_tv(self, ip_address: str) -> Optional[TVConfig]:
        return self.tvs.get(ip_address)

    def get_all_tvs(self) -> List[TVConfig]:
        return list(self.tvs.values())

    def update_tv(self, ip_address: str, tv_data: dict):
        if ip_address in self.tvs:
            current_tv = self.tvs[ip_address]
            updated_tv = current_tv.copy(update=tv_data)
            self.tvs[ip_address] = updated_tv
            self.save_config() 