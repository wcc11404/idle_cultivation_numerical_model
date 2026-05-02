export type PageMeta = { key: string; label: string; group: string }
export type Option = { id: string; name: string }
export type SpellOption = { spellId: string; name: string; type: string }

export type RealmsPayload = {
  config: any
  editor: Record<string, any>
}

export type RecipesPayload = {
  config: any
  rows: Record<string, any>[]
}

export type EnemiesPayload = {
  config: any
  rows: Record<string, any>[]
}

export type AreasPayload = {
  config: any
  overviewRows: Record<string, any>[]
  areaOptions: Option[]
  itemNameMap: Record<string, string>
  enemyNameMap: Record<string, string>
}

export type SpellsPayload = {
  config: any
  options: SpellOption[]
}

export type AppDrafts = {
  pages: PageMeta[]
  realms: RealmsPayload | null
  recipes: RecipesPayload | null
  enemies: EnemiesPayload | null
  areas: AreasPayload | null
  spells: SpellsPayload | null
}
