import type { AreasPayload, EnemiesPayload, PageMeta, RealmsPayload, RecipesPayload, SpellsPayload } from './types.js'

const jsonHeaders = { 'Content-Type': 'application/json' }

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function getPages(): Promise<PageMeta[]> {
  const data = await parse<{ pages: PageMeta[] }>(await fetch('/api/meta/pages'))
  return data.pages
}

export async function getRealms(): Promise<RealmsPayload> {
  return parse<RealmsPayload>(await fetch('/api/config/realms'))
}

export async function saveRealms(editor: Record<string, any>): Promise<RealmsPayload> {
  return parse<RealmsPayload>(
    await fetch('/api/config/realms', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ payload: { editor } }),
    }),
  )
}

export async function getRecipes(): Promise<RecipesPayload> {
  return parse<RecipesPayload>(await fetch('/api/config/recipes'))
}

export async function saveRecipes(rows: Record<string, any>[]): Promise<RecipesPayload> {
  return parse<RecipesPayload>(
    await fetch('/api/config/recipes', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ payload: { rows } }),
    }),
  )
}

export async function applyRecipeLadder(payload: Record<string, any>): Promise<Record<string, any>[]> {
  const data = await parse<{ rows: Record<string, any>[] }>(
    await fetch('/api/actions/recipes/apply-ladder', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ payload }),
    }),
  )
  return data.rows
}

export async function getEnemies(): Promise<EnemiesPayload> {
  return parse<EnemiesPayload>(await fetch('/api/config/enemies'))
}

export async function saveEnemies(rows: Record<string, any>[]): Promise<EnemiesPayload> {
  return parse<EnemiesPayload>(
    await fetch('/api/config/enemies', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ payload: { rows } }),
    }),
  )
}

export async function getAreas(): Promise<AreasPayload> {
  return parse<AreasPayload>(await fetch('/api/config/areas'))
}

export async function saveAreas(config: Record<string, any>): Promise<AreasPayload> {
  return parse<AreasPayload>(
    await fetch('/api/config/areas', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ payload: { config } }),
    }),
  )
}

export async function getSpells(): Promise<SpellsPayload> {
  return parse<SpellsPayload>(await fetch('/api/config/spells'))
}

export async function saveSpells(config: Record<string, any>): Promise<SpellsPayload> {
  return parse<SpellsPayload>(
    await fetch('/api/config/spells', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ payload: { config } }),
    }),
  )
}

export async function applySpellBatch(payload: Record<string, any>): Promise<Record<string, any>[]> {
  const data = await parse<{ rows: Record<string, any>[] }>(
    await fetch('/api/actions/spells/apply-batch', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ payload }),
    }),
  )
  return data.rows
}

export async function syncFromServer(): Promise<{ message: string }> {
  return parse<{ message: string }>(
    await fetch('/api/actions/sync-from-server', { method: 'POST' }),
  )
}

export async function getCultivationPreview(payload: Record<string, any>): Promise<any> {
  return parse<any>(
    await fetch('/api/preview/cultivation', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ payload }),
    }),
  )
}

export async function getBattlePreview(payload: Record<string, any>): Promise<any> {
  return parse<any>(
    await fetch('/api/preview/battle', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ payload }),
    }),
  )
}
