import logging
from quart import Quart, jsonify, request
from api.tv_routes import tv_bp, tv_service
from functools import wraps
import asyncio
import signal
import sys
import dotenv
import os

dotenv.load_dotenv()

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Quart(__name__)

# Enregistrement du blueprint
app.register_blueprint(tv_bp)

@app.route('/')
async def index():
    return jsonify({
        "name": "Samsung TV Control API",
        "version": "1.0.0",
        "description": "API REST pour contrôler une TV Samsung",
        "endpoints": {
            "tv_status": "/api/v1/tv/<ip_address>",
            "tv_power": "/api/v1/tv/<ip_address>/power",
            "tv_art_mode": "/api/v1/tv/<ip_address>/art-mode"
        }
    })

@app.route('/health')
async def health():
    return jsonify({
        "status": "ok",
        "version": "1.0.0"
    })

# Ajout du hook Quart pour la fermeture propre
@app.after_serving
async def shutdown():
    logger.info("Arrêt du service (after_serving)...")
    await tv_service.close_all() 