from quart import Blueprint, jsonify, request
from services.tv_service import TVService
import time
import os
import logging
from quart_cors import cors, route_cors


tv_bp = Blueprint('tv', __name__)
tv_service = TVService()

@tv_bp.route('/api/v1/tv/<ip_address>', methods=['GET'])
@route_cors(allow_origin="*")
async def get_tv_status(ip_address):
    start = time.time()
    result = await tv_service.get_tv_status(ip_address)
    duration = time.time() - start
    print(f"[PERF] get_tv_status({ip_address}) : {duration:.3f}s")
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)

@tv_bp.route('/api/v1/tv/<ip_address>/power', methods=['PUT'])
@route_cors(allow_origin="*")
async def power_control(ip_address):
    start = time.time()
    action = request.args.get('action', 'toggle')
    if action not in ['toggle', 'on', 'off']:
        return jsonify({
            "success": False,
            "error": f"Action '{action}' non supportée. Utilisez 'toggle', 'on' ou 'off'"
        }), 400
    
    result = await tv_service.power_control(ip_address, action)
    duration = time.time() - start
    print(f"[PERF] power_control({ip_address}, action={action}) : {duration:.3f}s")
    return jsonify(result)

@tv_bp.route('/api/v1/tv/<ip_address>/art-mode', methods=['PUT'])
@route_cors(allow_origin="*")
async def set_art_mode(ip_address):
    start = time.time()
    action = request.args.get('action', 'toggle')
    if action not in ['toggle', 'on', 'off']:
        return jsonify({
            "success": False,
            "error": f"Action '{action}' non supportée. Utilisez 'toggle', 'on' ou 'off'"
        }), 400
    
    result = await tv_service.set_art_mode(ip_address, action)
    duration = time.time() - start
    print(f"[PERF] set_art_mode({ip_address}, action={action}) : {duration:.3f}s")
    return jsonify(result)

@tv_bp.route('/api/v1/tv/<ip_address>/upload', methods=['POST'])
@route_cors(allow_origin="*")
async def upload_photo(ip_address):
    files = await request.files
    if 'file' not in files:
        return jsonify({"success": False, "error": "Aucun fichier reçu"}), 400
    file = files['file']
    file_bytes = file.read()
    file_type = file.filename.split('.')[-1]
    matte = request.args.get('matte', 'shadowbox_polar')
    portrait_matte = request.args.get('portrait_matte', 'shadowbox_polar')
    result = await tv_service.upload_photo(ip_address, file_bytes, file_type, matte, portrait_matte)
    if not result.get("success"):
        return jsonify(result), 500
    return jsonify(result)

@tv_bp.route('/api/v1/tv/<ip_address>/upload-folder', methods=['POST'])
@route_cors(allow_origin="*")
async def upload_folder(ip_address):
    folder_path = os.environ.get('TV_IMAGE_FOLDER')
    extensions_env = os.environ.get('TV_IMAGE_EXTENSIONS')
    if not folder_path:
        return jsonify({"success": False, "error": "La variable d'environnement TV_IMAGE_FOLDER n'est pas définie."}), 400
    if not extensions_env:
        return jsonify({"success": False, "error": "La variable d'environnement TV_IMAGE_EXTENSIONS n'est pas définie."}), 400
    extensions = tuple(f'.{ext.strip().lower()}' for ext in extensions_env.split(','))
    if not os.path.isdir(folder_path):
        return jsonify({"success": False, "error": f"Dossier introuvable : {folder_path}"}), 400
    logger = logging.getLogger("upload-folder")
    results = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(extensions):
            with open(os.path.join(folder_path, filename), 'rb') as f:
                file_bytes = f.read()
            file_type = filename.split('.')[-1]
            result = await tv_service.upload_photo(ip_address, file_bytes, file_type)
            logger.info(f"[UPLOAD DEBUG] Fichier: {filename} | Résultat: {result}")
            results.append({
                "filename": filename,
                "success": result.get("success", False),
                "error": result.get("error") if not result.get("success", False) else None,
                "content_id": result.get("content_id") if result.get("success", False) else None,
                "raw_result": result  # Pour debug
            })
    return jsonify(results)

@tv_bp.route('/api/v1/tv/<ip_address>/art-images', methods=['GET'])
@route_cors(allow_origin="*")
async def list_art_images(ip_address):
    start = time.time()
    result = await tv_service.list_art_images(ip_address)
    duration = time.time() - start
    print(f"[PERF] list_art_images({ip_address}) : {duration:.3f}s")
    if not result.get("success"):
        return jsonify(result), 500
    return jsonify(result)

@tv_bp.route('/api/v1/tv/<ip_address>/art-images', methods=['DELETE'])
@route_cors(allow_origin="*")
async def delete_art_images(ip_address):
    data = await request.get_json(force=True)
    content_ids = data.get('content_ids') if data else None
    # Si content_ids est vide ou absent, on supprime toutes les images
    if not content_ids:
        # On récupère d'abord la liste complète
        images_result = await tv_service.list_art_images(ip_address)
        if not images_result.get('success'):
            return jsonify(images_result), 500
        content_ids = [img['content_id'] for img in images_result['images']]
    result = await tv_service.delete_art_images(ip_address, content_ids)
    if not result.get('success'):
        return jsonify(result), 500
    return jsonify(result)

@tv_bp.route('/api/v1/tvs', methods=['GET'])
@route_cors(allow_origin="*")
async def get_all_tvs():
    tvs = tv_service.config_service.get_tvs()
    return jsonify(tvs) 