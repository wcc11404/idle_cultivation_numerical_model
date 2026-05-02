from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import service

ROOT = Path(__file__).resolve().parents[1]
WEB_DIST = ROOT / 'web' / 'dist'


class NoCacheStaticFiles(StaticFiles):
    def file_response(self, full_path: str, stat_result, scope, status_code: int = 200) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

app = FastAPI(title='Idle Cultivation Numerical Model')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class JsonPayload(BaseModel):
    payload: dict


@app.get('/api/meta/pages')
def get_pages():
    return {'pages': service.get_meta_pages()}


@app.get('/api/config/realms')
def get_realms():
    return service.get_realms_payload()


@app.post('/api/config/realms')
def save_realms(payload: JsonPayload):
    return service.save_realms_payload(payload.payload['editor'])


@app.get('/api/config/recipes')
def get_recipes():
    return service.get_recipes_payload()


@app.post('/api/config/recipes')
def save_recipes(payload: JsonPayload):
    return service.save_recipes_payload(payload.payload['rows'])


@app.get('/api/config/enemies')
def get_enemies():
    return service.get_enemies_payload()


@app.post('/api/config/enemies')
def save_enemies(payload: JsonPayload):
    return service.save_enemies_payload(payload.payload['rows'])


@app.get('/api/config/areas')
def get_areas():
    return service.get_areas_payload()


@app.post('/api/config/areas')
def save_areas(payload: JsonPayload):
    return service.save_areas_payload(payload.payload['config'])


@app.get('/api/config/spells')
def get_spells():
    return service.get_spells_payload()


@app.post('/api/config/spells')
def save_spells(payload: JsonPayload):
    return service.save_spells_payload(payload.payload['config'])


@app.post('/api/actions/recipes/apply-ladder')
def apply_recipe_ladder(payload: JsonPayload):
    return {'rows': service.apply_recipe_ladder(payload.payload)}


@app.post('/api/actions/spells/apply-batch')
def apply_spell_batch(payload: JsonPayload):
    return {'rows': service.apply_spell_batch(payload.payload)}


@app.post('/api/actions/sync-from-server')
def sync_from_server():
    return service.sync_local_data_from_server()


@app.get('/api/preview/cultivation')
def get_cultivation_preview():
    base = service.load_all_configs()
    realms_editor = service.get_realms_payload()['editor']
    recipes_rows = service.get_recipes_payload()['rows']
    enemy_rows = service.get_enemies_payload()['rows']
    return service.build_cultivation_preview({
        'realmsEditor': realms_editor,
        'recipeRows': recipes_rows,
        'areasConfig': base['areas'],
        'enemyRows': enemy_rows,
    })


@app.post('/api/preview/cultivation')
def post_cultivation_preview(payload: JsonPayload):
    return service.build_cultivation_preview(payload.payload)


@app.get('/api/preview/battle')
def get_battle_preview():
    base = service.load_all_configs()
    realms_editor = service.get_realms_payload()['editor']
    enemy_rows = service.get_enemies_payload()['rows']
    first_area = next(iter(base['areas'].get('normal_areas', {}).keys()), '')
    return service.build_battle_preview({
        'realmsEditor': realms_editor,
        'areasConfig': base['areas'],
        'enemyRows': enemy_rows,
        'realm_name': '炼气期',
        'level': 1,
        'area_id': first_area,
    })


@app.post('/api/preview/battle')
def post_battle_preview(payload: JsonPayload):
    return service.build_battle_preview(payload.payload)


if WEB_DIST.exists():
    assets_dir = WEB_DIST / 'assets'
    if assets_dir.exists():
        app.mount('/assets', NoCacheStaticFiles(directory=assets_dir), name='assets')


@app.get('/api/health')
def health():
    return {'ok': True}


@app.get('/{full_path:path}')
def serve_spa(full_path: str):
    if WEB_DIST.exists():
        candidate = WEB_DIST / full_path
        if full_path and candidate.exists() and candidate.is_file():
            response = FileResponse(candidate)
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        index_file = WEB_DIST / 'index.html'
        if index_file.exists():
            response = FileResponse(index_file)
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
    return HTMLResponse('<h1>Web build not found</h1><p>Please run restart.sh to build the React frontend.</p>', status_code=503)
