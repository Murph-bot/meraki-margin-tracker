import { describe, expect, it } from 'vitest'
import el from './locales/el.json'
import en from './locales/en.json'

type Tree = { [key: string]: string | Tree }

function flatten(tree: Tree, prefix = ''): Record<string, string> {
  const out: Record<string, string> = {}
  for (const [key, value] of Object.entries(tree)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (typeof value === 'string') out[path] = value
    else Object.assign(out, flatten(value, path))
  }
  return out
}

const vars = (s: string) => [...s.matchAll(/{{\s*([\w.]+)\s*}}/g)].map(m => m[1]).sort()
const flatEl = flatten(el as Tree)
const flatEn = flatten(en as Tree)

describe('locale files', () => {
  it('have the same keys in both directions', () => {
    const missingInEn = Object.keys(flatEl).filter(k => !(k in flatEn))
    const missingInEl = Object.keys(flatEn).filter(k => !(k in flatEl))
    expect({ missingInEn, missingInEl }).toEqual({ missingInEn: [], missingInEl: [] })
  })

  it('use the same interpolation variables', () => {
    const mismatched = Object.keys(flatEl)
      .filter(k => k in flatEn && vars(flatEl[k]).join() !== vars(flatEn[k]).join())
      .map(k => `${k}: el={${vars(flatEl[k])}} en={${vars(flatEn[k])}}`)
    expect(mismatched).toEqual([])
  })

  it('contain no empty strings', () => {
    const empty = [
      ...Object.entries(flatEl).filter(([, v]) => !v.trim()).map(([k]) => `el:${k}`),
      ...Object.entries(flatEn).filter(([, v]) => !v.trim()).map(([k]) => `en:${k}`),
    ]
    expect(empty).toEqual([])
  })
})
