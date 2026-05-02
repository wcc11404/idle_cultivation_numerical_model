from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_meta_pages_and_health() -> None:
    health = client.get('/api/health')
    assert health.status_code == 200
    assert health.json()['ok'] is True

    pages = client.get('/api/meta/pages')
    assert pages.status_code == 200
    payload = pages.json()['pages']
    keys = {page['key'] for page in payload}
    assert {'cultivation', 'battle', 'areas', 'realms', 'enemies', 'recipes', 'spells'} <= keys


def test_spell_batch_action() -> None:
    payload = {
        'rows': [
            {'level': 1, 'spirit_cost': 10, 'use_count_required': 2},
            {'level': 2, 'spirit_cost': 0, 'use_count_required': 0},
            {'level': 3, 'spirit_cost': 0, 'use_count_required': 0},
            {'level': 4, 'spirit_cost': 0, 'use_count_required': 0},
            {'level': 5, 'spirit_cost': 0, 'use_count_required': 0},
        ],
        'level2_to_4_spirit_multiplier': 5,
        'level5_plus_spirit_multiplier': 4,
        'level1_to_4_use_multiplier': 10,
        'level5_plus_use_multiplier': 6,
    }
    response = client.post('/api/actions/spells/apply-batch', json={'payload': payload})
    assert response.status_code == 200
    rows = response.json()['rows']
    assert rows[1]['spirit_cost'] == 50
    assert rows[1]['use_count_required'] == 20
    assert rows[2]['spirit_cost'] == 250
    assert rows[2]['use_count_required'] == 200
    assert rows[3]['spirit_cost'] == 1250
    assert rows[3]['use_count_required'] == 2000
    assert rows[4]['spirit_cost'] == 5000
    assert rows[4]['use_count_required'] == 12000


def test_spell_batch_action_can_update_only_use_count() -> None:
    payload = {
        'rows': [
            {'level': 1, 'spirit_cost': 10, 'use_count_required': 2},
            {'level': 2, 'spirit_cost': 50, 'use_count_required': 20},
            {'level': 3, 'spirit_cost': 250, 'use_count_required': 20},
            {'level': 4, 'spirit_cost': 1250, 'use_count_required': 20},
            {'level': 5, 'spirit_cost': 5000, 'use_count_required': 120},
        ],
        'level2_to_4_spirit_multiplier': None,
        'level5_plus_spirit_multiplier': None,
        'level1_to_4_use_multiplier': 5,
        'level5_plus_use_multiplier': 3,
    }
    response = client.post('/api/actions/spells/apply-batch', json={'payload': payload})
    assert response.status_code == 200
    rows = response.json()['rows']
    assert rows[1]['spirit_cost'] == 50
    assert rows[2]['spirit_cost'] == 250
    assert rows[3]['spirit_cost'] == 1250
    assert rows[4]['spirit_cost'] == 5000
    assert rows[1]['use_count_required'] == 10
    assert rows[2]['use_count_required'] == 50
    assert rows[3]['use_count_required'] == 250
    assert rows[4]['use_count_required'] == 750


def test_preview_endpoints() -> None:
    cultivation = client.get('/api/preview/cultivation')
    assert cultivation.status_code == 200
    assert 'metrics' in cultivation.json()

    battle = client.get('/api/preview/battle')
    assert battle.status_code == 200
    assert 'custom' in battle.json()


def test_cultivation_preview_hides_zero_duration_text() -> None:
    cultivation = client.get('/api/preview/cultivation')
    assert cultivation.status_code == 200
    payload = cultivation.json()

    realm_summary = payload['realmSummary']['base']
    summary_by_realm = {row['大境界']: row for row in realm_summary}
    assert summary_by_realm['元婴期']['该境界灵石总耗时'] != ''
    assert summary_by_realm['化神期']['该境界灵石总耗时'] != ''
    assert summary_by_realm['炼虚期']['该境界灵石总耗时'] != ''

    detail_rows = payload['upgradeDetail']['base']
    zero_like_fields = [
        row[key]
        for row in detail_rows
        for key in ('层间灵石耗时', '层间材料耗时', '累计材料耗时')
        if row[key] == ''
    ]
    assert zero_like_fields, '应至少存在一批被隐藏为空白的零耗时字段'
