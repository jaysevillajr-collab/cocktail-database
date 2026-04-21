import { useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts'

const RAW_API_BASE = (import.meta.env.VITE_API_BASE || (import.meta.env.PROD ? '' : 'http://127.0.0.1:8002')).trim()
const API_BASE = RAW_API_BASE.replace(/\/+$/, '')
const APP_VERSION = 'v1.0.0'
const SAVED_VIEWS_KEY = 'cocktail_web_saved_views_v1'
const EDIT_UNLOCK_SESSION_KEY = 'cocktail_web_edit_unlock_at_v1'
const EDIT_ACCESS_PASSWORD = 'knocktwiceonly'
const EDIT_UNLOCK_MAX_AGE_MS = 60 * 60 * 1000
const EDIT_LOCKED_MESSAGE = 'Editing is locked. Enter the password in Settings to continue.'
const EMPTY_ALCOHOL_FORM = {
  Brand: '',
  Base_Liquor: '',
  Type: '',
  ABV: '',
  Country: '',
  Price_NZD_700ml: '',
  Taste: '',
  Substitute: '',
  Availability: '',
  image_path: ''
}

function formatShortMonth(value) {
  const raw = String(value || '').trim()
  if (!raw) return '-'
  const parsed = new Date(`${raw}-01T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return raw
  return parsed.toLocaleDateString(undefined, { month: 'short' })
}

const MAX_SCORE = 5
const FIVE_SCALE_FIELDS = new Set(['Rating_Jason', 'Rating_Jaime', 'Rating_overall', 'Difficulty'])

function normalizeDecimalForTyping(rawValue) {
  const nextValue = String(rawValue ?? '')
  if (nextValue === '') return ''
  if (!/^\d*\.?\d*$/.test(nextValue)) return null
  if ((nextValue.match(/\./g) || []).length > 1) return null
  if (nextValue.startsWith('.')) return `0${nextValue}`
  return nextValue
}

function normalizeFiveScaleInput(rawValue) {
  const normalized = normalizeDecimalForTyping(rawValue)
  if (normalized === null) return null
  if (normalized === '') return ''
  const numeric = Number(normalized)
  if (Number.isNaN(numeric) || numeric < 0 || numeric > MAX_SCORE) return null
  return normalized
}

function isValidFiveScaleValue(rawValue) {
  const text = String(rawValue ?? '').trim()
  if (!text) return true
  const numeric = Number(text)
  return !Number.isNaN(numeric) && numeric >= 0 && numeric <= MAX_SCORE
}

function formatNumericString(value) {
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return String(value || '').trim()
  return Number.isInteger(numeric) ? String(numeric) : String(Math.round(numeric * 10) / 10)
}

function normalizeAbvValue(rawValue) {
  const text = String(rawValue || '').trim()
  if (!text) return ''
  return text.includes('%') ? text : `${text}%`
}

function normalizePriceValue(rawValue) {
  const text = String(rawValue || '').trim()
  if (!text) return ''
  return text.startsWith('$') ? text : `$${text}`
}

function normalizeDifficultyOutOfFive(rawDifficulty) {
  const value = String(rawDifficulty || '').trim()
  if (!value) return ''

  const lowered = value.toLowerCase()
  const aliases = {
    easy: 2,
    low: 2,
    medium: 3,
    moderate: 3,
    hard: 4,
    advanced: 4,
    expert: 5
  }

  let numeric = aliases[lowered]
  if (numeric == null) {
    const parsed = Number(value.replace(/[^\d.]/g, ''))
    if (!Number.isNaN(parsed)) {
      numeric = Math.max(0, Math.min(MAX_SCORE, parsed))
    }
  }

  if (numeric == null) return ''
  return `${formatNumericString(numeric)} out of 5`
}

const EMPTY_COST_INSIGHTS = {
  avg_bottle_price_nzd: null,
  estimated_cost_per_serving_nzd_avg: null,
  top_expensive_bottles: [],
  base_spirit_avg_price: [],
  tasting_monthly_estimated_cost: [],
  cocktail_estimated_costs: []
}

const EMPTY_STORAGE_SETTINGS = {
  root_path: '',
  db_path: '',
  images_path: '',
  local_db_path: '',
  local_images_path: '',
  dual_save_enabled: false,
  backup_configured: false,
  active_db_last_write_at: '',
  local_db_last_write_at: '',
  last_mirror_sync_at: '',
  db_source: '',
  images_source: ''
}

const TASTING_DIMENSIONS = [
  { key: 'sweetness', label: 'Sweetness' },
  { key: 'sourness', label: 'Sourness' },
  { key: 'bitterness', label: 'Bitterness' },
  { key: 'booziness', label: 'Booziness' },
  { key: 'body', label: 'Body' },
  { key: 'aroma', label: 'Aroma' },
  { key: 'balance', label: 'Balance' },
  { key: 'finish', label: 'Finish' }
]

function buildEmptyTastingForm() {
  return {
    date: new Date().toISOString().slice(0, 10),
    cocktail_name: '',
    rating: '',
    notes: '',
    mood: '',
    occasion: '',
    location: '',
    would_make_again: '',
    change_next_time: '',
    sweetness: '',
    sourness: '',
    bitterness: '',
    booziness: '',
    body: '',
    aroma: '',
    balance: '',
    finish: ''
  }
}

function formatDateTime(value) {
  const raw = String(value || '').trim()
  if (!raw) return '-'
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) return raw
  return parsed.toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const EMPTY_TASTING_INSIGHTS = {
  entries: 0,
  avg_rating: null,
  would_make_again_rate_pct: null,
  top_cocktails: [],
  mood_breakdown: [],
  flavor_profile_avg: [],
  rating_by_base_spirit: [],
  monthly_activity: []
}

const EMPTY_COCKTAIL_FORM = {
  Cocktail_Name: '',
  Ingredients: '',
  Rating_Jason: '',
  Rating_Jaime: '',
  Rating_overall: '',
  Base_spirit_1: '',
  Type1: '',
  Brand1: '',
  Base_spirit_2: '',
  Type2: '',
  Brand2: '',
  Citrus: '',
  Garnish: '',
  Notes: '',
  DatetimeAdded: '',
  Prep_Time: '',
  Difficulty: '',
  image_path: ''
}

const CHART_SWATCH = ['#7a4f24', '#a86f35', '#c48b45', '#d9ab66', '#e9c998', '#f2dec0']

function mapAlcoholRowToForm(row) {
  return {
    Brand: row?.Brand || '',
    Base_Liquor: row?.Base_Liquor || '',
    Type: row?.Type || '',
    ABV: row?.ABV || '',
    Country: row?.Country || '',
    Price_NZD_700ml: row?.Price_NZD_700ml || '',
    Taste: row?.Taste || '',
    Substitute: row?.Substitute || '',
    Availability: row?.Availability || '',
    image_path: row?.image_path || ''
  }
}

function normalizeSavedView(item) {
  const payload = item?.payload || {}
  return {
    id: item.id,
    name: item.name,
    tab: payload.tab || 'alcohol',
    query: payload.query || '',
    filters: payload.filters || {},
    createdAt: item.created_at || item.createdAt || ''
  }
}

function normalizeAiSuggestion(item, index = 0) {
  if (typeof item === 'string') {
    return {
      name: `Twist ${index + 1}`,
      flavor_goal: item,
      substitutions: [],
      method: [],
      garnish_and_glass: '',
      why_it_works: '',
      difficulty: '',
      risk_note: '',
      wild_card: ''
    }
  }

  const substitutions = Array.isArray(item?.substitutions)
    ? item.substitutions.filter((value) => String(value).trim()).map((value) => String(value).trim())
    : []

  const method = Array.isArray(item?.method)
    ? item.method.filter((value) => String(value).trim()).map((value) => String(value).trim())
    : []

  return {
    name: item?.name || `Twist ${index + 1}`,
    flavor_goal: item?.flavor_goal || '',
    substitutions,
    method,
    garnish_and_glass: item?.garnish_and_glass || '',
    why_it_works: item?.why_it_works || '',
    difficulty: normalizeDifficultyOutOfFive(item?.difficulty),
    risk_note: item?.risk_note || '',
    wild_card: item?.wild_card || ''
  }
}

function mapCocktailRowToForm(row) {
  return {
    Cocktail_Name: row?.Cocktail_Name || '',
    Ingredients: row?.Ingredients || '',
    Rating_Jason: row?.Rating_Jason || '',
    Rating_Jaime: row?.Rating_Jaime || '',
    Rating_overall: row?.Rating_overall || '',
    Base_spirit_1: row?.Base_spirit_1 || '',
    Type1: row?.Type1 || '',
    Brand1: row?.Brand1 || '',
    Base_spirit_2: row?.Base_spirit_2 || '',
    Type2: row?.Type2 || '',
    Brand2: row?.Brand2 || '',
    Citrus: row?.Citrus || '',
    Garnish: row?.Garnish || '',
    Notes: row?.Notes || '',
    DatetimeAdded: row?.DatetimeAdded || '',
    Prep_Time: row?.Prep_Time || '',
    Difficulty: row?.Difficulty || '',
    image_path: row?.image_path || ''
  }
}

function normalizeTastingItem(item) {
  return {
    id: item.id,
    date: item.date,
    cocktailName: item.cocktail_name || item.cocktailName || '',
    rating: item.rating || '',
    notes: item.notes || '',
    mood: item.mood || '',
    occasion: item.occasion || '',
    location: item.location || '',
    wouldMakeAgain: item.would_make_again || item.wouldMakeAgain || '',
    changeNextTime: item.change_next_time || item.changeNextTime || '',
    sweetness: item.sweetness || '',
    sourness: item.sourness || '',
    bitterness: item.bitterness || '',
    booziness: item.booziness || '',
    body: item.body || '',
    aroma: item.aroma || '',
    balance: item.balance || '',
    finish: item.finish || '',
    createdAt: item.created_at || item.createdAt || ''
  }
}

function normalizeIngredientToken(value) {
  return value
    .toLowerCase()
    .replace(/\([^)]*\)/g, ' ')
    .replace(/\b\d+[\d./]*\b/g, ' ')
    .replace(/\b(oz|ml|dash|dashes|tbsp|tsp|slice|slices|part|parts|cup|cups)\b/g, ' ')
    .replace(/[^a-z\s-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function parseIngredientText(value) {
  if (!value) return []
  const rawTokens = value.split(/[,\n]/g)
  return rawTokens
    .map((token) => normalizeIngredientToken(token))
    .filter((token) => token.length >= 2)
}

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function resolveImageUrl(imagePath) {
  const raw = String(imagePath || '').trim()
  if (!raw) return ''

  if (raw.startsWith('http://') || raw.startsWith('https://') || raw.startsWith('data:')) {
    return raw
  }

  const normalized = raw.replace(/\\/g, '/').replace(/^\.\//, '')
  if (normalized.startsWith('/')) {
    return `${API_BASE}${normalized}`
  }

  return `${API_BASE}/${normalized}`
}

function slugifyFileLabel(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function formatFileTimestamp(date = new Date()) {
  const yyyy = String(date.getFullYear())
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mi = String(date.getMinutes()).padStart(2, '0')
  const ss = String(date.getSeconds()).padStart(2, '0')
  return `${yyyy}${mm}${dd}-${hh}${mi}${ss}`
}

const MAX_EDITOR_IMAGE_BYTES = 5 * 1024 * 1024
const MAX_EDITOR_IMAGE_DIMENSION = 2400

function loadImageElement(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const image = new Image()
    image.onload = () => {
      URL.revokeObjectURL(url)
      resolve(image)
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Failed to decode image file.'))
    }
    image.src = url
  })
}

function canvasToJpegBlob(canvas, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error('Failed to encode image as JPEG.'))
        return
      }
      resolve(blob)
    }, 'image/jpeg', quality)
  })
}

async function compressImageToUploadJpeg(file, maxBytes = MAX_EDITOR_IMAGE_BYTES) {
  if (!file || !String(file.type || '').startsWith('image/')) {
    throw new Error('Please use a valid image file.')
  }

  const image = await loadImageElement(file)
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d')
  if (!context) {
    throw new Error('Image processing is not supported in this browser.')
  }

  let width = Number(image.naturalWidth || image.width || 0)
  let height = Number(image.naturalHeight || image.height || 0)
  if (!width || !height) {
    throw new Error('Could not read image dimensions.')
  }

  const maxDimension = Math.max(width, height)
  if (maxDimension > MAX_EDITOR_IMAGE_DIMENSION) {
    const scale = MAX_EDITOR_IMAGE_DIMENSION / maxDimension
    width = Math.max(1, Math.round(width * scale))
    height = Math.max(1, Math.round(height * scale))
  }

  let quality = 0.9
  let attempt = 0
  let lastBlob = null

  while (attempt < 14) {
    canvas.width = width
    canvas.height = height
    context.clearRect(0, 0, width, height)
    context.drawImage(image, 0, 0, width, height)

    const blob = await canvasToJpegBlob(canvas, quality)
    lastBlob = blob

    if (blob.size <= maxBytes) {
      const stem = String(file.name || 'image').replace(/\.[^.]+$/, '').replace(/\s+/g, '-').replace(/[^a-zA-Z0-9_-]/g, '') || 'image'
      return new File([blob], `${stem}.jpg`, {
        type: 'image/jpeg',
        lastModified: Date.now()
      })
    }

    if (quality > 0.56) {
      quality = Math.max(0.5, quality - 0.08)
    } else {
      width = Math.max(1, Math.round(width * 0.85))
      height = Math.max(1, Math.round(height * 0.85))
      quality = 0.86
    }

    attempt += 1
  }

  throw new Error(
    `Could not compress image under 5MB${lastBlob ? ` (current ${(lastBlob.size / (1024 * 1024)).toFixed(1)}MB)` : ''}. Please choose a smaller image.`
  )
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('Failed to read image file'))
    reader.readAsDataURL(file)
  })
}

function clipboardImageFile(event) {
  const items = Array.from(event?.clipboardData?.items || [])
  const imageItem = items.find((item) => String(item.type || '').startsWith('image/'))
  if (!imageItem) return null
  return imageItem.getAsFile()
}

function prettyLabel(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function normalizeNameKey(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
}

function baseFamilyFromBaseLiquor(baseValue) {
  const normalized = normalizeNameKey(baseValue)
  if (normalized.includes('gin')) return 'gin'
  if (normalized.includes('rum') || normalized.includes('rhum') || normalized.includes('cachaca')) return 'rum'
  if (normalized.includes('tequila')) return 'tequila'
  if (normalized.includes('mezcal')) return 'mezcal'
  if (normalized.includes('vodka')) return 'vodka'
  if (normalized.includes('brandy') || normalized.includes('cognac') || normalized.includes('armagnac')) return 'brandy'
  if (normalized.includes('whiskey') || normalized.includes('whisky') || normalized.includes('scotch') || normalized.includes('bourbon') || normalized.includes('rye')) return 'whiskey'
  if (normalized.includes('liqueur') || normalized.includes('liquor') || normalized.includes('amaro') || normalized.includes('aperitif') || normalized.includes('aperitivo')) return 'liqueur'
  return ''
}

function suggestLiquorSubtypeOptions(brandValue, baseLiquorValue) {
  const brand = normalizeNameKey(brandValue)
  const base = normalizeNameKey(baseLiquorValue)
  if (!brand || !base) return { family: '', options: [] }

  const includesAny = (text, terms) => terms.some((term) => text.includes(term))
  const uniqueNonEmpty = (items) => [...new Set(items.filter(Boolean))]

  let family = ''
  if (includesAny(base, ['gin'])) family = 'gin'
  else if (includesAny(base, ['rum', 'rhum', 'cachaca'])) family = 'rum'
  else if (includesAny(base, ['tequila'])) family = 'tequila'
  else if (includesAny(base, ['mezcal'])) family = 'mezcal'
  else if (includesAny(base, ['vodka'])) family = 'vodka'
  else if (includesAny(base, ['brandy', 'cognac', 'armagnac'])) family = 'brandy'
  else if (includesAny(base, ['whisky', 'whiskey', 'scotch', 'bourbon', 'rye'])) family = 'whiskey'
  else if (includesAny(base, ['liqueur', 'liquor', 'amaro', 'aperitif', 'aperitivo'])) family = 'liqueur'

  if (!family) return { family: '', options: [] }

  const familyRules = {
    gin: [
      { keywords: ['plymouth'], styles: ['Plymouth Gin'] },
      { keywords: ['hendrick'], styles: ['New Western Dry Gin'] },
      { keywords: ['tanqueray', 'beefeater', 'bombay', 'gordon', 'sipsmith'], styles: ['London Dry Gin', 'Distilled Gin'] },
      { keywords: ['old tom'], styles: ['Old Tom Gin'] }
    ],
    rum: [
      { keywords: ['zacapa', 'diplomatico', 'el dorado'], styles: ['Aged Rum', 'Dark Rum'] },
      { keywords: ['captain morgan', 'kraken', 'sailor jerry'], styles: ['Spiced Rum', 'Dark Rum'] },
      { keywords: ['bacardi', 'havana club 3', 'plantation 3', '3 stars'], styles: ['White Rum', 'Light Rum'] },
      { keywords: ['gosling', 'myers', 'coruba'], styles: ['Dark Rum', 'Black Rum'] }
    ],
    tequila: [
      { keywords: ['don julio 1942', 'clase azul', 'extra anejo', 'extra añejo'], styles: ['Extra Anejo Tequila', 'Anejo Tequila'] },
      { keywords: ['don julio reposado', 'herradura reposado', 'cazadores reposado', 'reposado'], styles: ['Reposado Tequila', 'Blanco Tequila'] },
      { keywords: ['anejo', 'añejo'], styles: ['Anejo Tequila', 'Extra Anejo Tequila'] },
      { keywords: ['blanco', 'silver', 'plata'], styles: ['Blanco Tequila'] }
    ],
    mezcal: [
      { keywords: ['joven'], styles: ['Joven Mezcal'] },
      { keywords: ['reposado'], styles: ['Reposado Mezcal', 'Joven Mezcal'] },
      { keywords: ['anejo', 'añejo'], styles: ['Anejo Mezcal', 'Reposado Mezcal'] }
    ],
    vodka: [
      { keywords: ['grey goose', 'ketel one', 'belvedere', 'absolut', 'stolichnaya'], styles: ['Classic Vodka', 'Neutral Vodka'] },
      { keywords: ['citron', 'vanilla', 'raspberry', 'flavored', 'flavoured'], styles: ['Flavored Vodka'] }
    ],
    brandy: [
      { keywords: ['hennessy', 'martell', 'remy martin', 'rémy martin', 'courvoisier'], styles: ['Cognac'] },
      { keywords: ['armagnac'], styles: ['Armagnac'] },
      { keywords: ['calvados'], styles: ['Calvados'] }
    ],
    whiskey: [
      { keywords: ['jack daniel', 'jim beam', 'maker\'s mark', 'wild turkey', 'woodford'], styles: ['Bourbon Whiskey', 'Tennessee Whiskey'] },
      { keywords: ['bulleit rye', 'sazerac rye', 'rittenhouse', 'whistlepig', 'rye'], styles: ['Rye Whiskey', 'Straight Rye Whiskey'] },
      { keywords: ['jameson', 'redbreast', 'powers', 'tullamore'], styles: ['Irish Whiskey'] },
      { keywords: ['jura', 'talisker', 'lagavulin', 'laphroaig', 'ardbeg', 'glenfiddich', 'glenlivet', 'chivas'], styles: ['Scotch Whisky', 'Single Malt Scotch'] }
    ],
    liqueur: [
      { keywords: ['campari', 'aperol'], styles: ['Bitter Aperitif', 'Aperitivo'] },
      { keywords: ['cointreau', 'triple sec', 'curaçao', 'curacao', 'grand marnier'], styles: ['Orange Liqueur', 'Triple Sec'] },
      { keywords: ['amaro', 'montenegro', 'averna', 'nonino', 'fernet'], styles: ['Amaro', 'Herbal Liqueur'] }
    ]
  }

  const defaults = {
    gin: ['London Dry Gin', 'Distilled Gin', 'Old Tom Gin'],
    rum: ['White Rum', 'Dark Rum', 'Spiced Rum', 'Aged Rum'],
    tequila: ['Blanco Tequila', 'Reposado Tequila', 'Anejo Tequila'],
    mezcal: ['Joven Mezcal', 'Reposado Mezcal', 'Anejo Mezcal'],
    vodka: ['Classic Vodka', 'Flavored Vodka'],
    brandy: ['Brandy', 'Cognac', 'Armagnac'],
    whiskey: ['Whiskey', 'Bourbon Whiskey', 'Rye Whiskey', 'Scotch Whisky', 'Irish Whiskey'],
    liqueur: ['Liqueur', 'Amaro', 'Bitter Aperitif', 'Orange Liqueur']
  }

  const matchedStyles = []
  const rules = familyRules[family] || []
  for (const rule of rules) {
    if (includesAny(brand, rule.keywords)) {
      matchedStyles.push(...rule.styles)
    }
  }

  const options = uniqueNonEmpty([...matchedStyles, ...(defaults[family] || [])])
  return { family, options }
}

function findBestAlcoholPrefillSource(rows, form) {
  const brandKey = normalizeNameKey(form.Brand)
  const baseKey = normalizeNameKey(form.Base_Liquor)
  const typeKey = normalizeNameKey(form.Type)
  if (!brandKey) return null

  const candidates = rows
    .map((row) => {
      const rowBrand = normalizeNameKey(row.Brand)
      const rowBase = normalizeNameKey(row.Base_Liquor)
      const rowType = normalizeNameKey(row.Type)

      if (rowBrand !== brandKey) {
        return null
      }

      let score = 10
      if (baseKey && rowBase === baseKey) score += 5
      if (typeKey && rowType === typeKey) score += 4

      const filledCount = [row.Country, row.Price_NZD_700ml, row.ABV, row.Substitute]
        .filter((value) => String(value || '').trim())
        .length
      score += filledCount

      return { row, score }
    })
    .filter(Boolean)
    .sort((a, b) => b.score - a.score)

  return candidates[0]?.row || null
}

export default function App() {
  const [loading, setLoading] = useState(true)
  const [counts, setCounts] = useState(null)
  const [alcohol, setAlcohol] = useState([])
  const [cocktails, setCocktails] = useState([])
  const [mainSection, setMainSection] = useState('library')
  const [activeTab, setActiveTab] = useState('alcohol')
  const [query, setQuery] = useState('')
  const [alcoholBaseLiquorFilter, setAlcoholBaseLiquorFilter] = useState('all')
  const [alcoholAvailabilityFilter, setAlcoholAvailabilityFilter] = useState('all')
  const [cocktailBaseSpiritFilter, setCocktailBaseSpiritFilter] = useState('all')
  const [cocktailMinRatingFilter, setCocktailMinRatingFilter] = useState('')
  const [cocktailMaxDifficultyFilter, setCocktailMaxDifficultyFilter] = useState('all')
  const [selectedAlcohol, setSelectedAlcohol] = useState(null)
  const [selectedCocktail, setSelectedCocktail] = useState(null)
  const [alcoholForm, setAlcoholForm] = useState(EMPTY_ALCOHOL_FORM)
  const [cocktailForm, setCocktailForm] = useState(EMPTY_COCKTAIL_FORM)
  const [alcoholEditorMode, setAlcoholEditorMode] = useState('view')
  const [cocktailEditorMode, setCocktailEditorMode] = useState('view')
  const [alcoholImageCandidates, setAlcoholImageCandidates] = useState([])
  const [alcoholImageFetchLoading, setAlcoholImageFetchLoading] = useState(false)
  const [alcoholImageSaveLoadingUrl, setAlcoholImageSaveLoadingUrl] = useState('')
  const [savedViews, setSavedViews] = useState([])
  const [costInsights, setCostInsights] = useState(EMPTY_COST_INSIGHTS)
  const [viewName, setViewName] = useState('')
  const [tastingLogs, setTastingLogs] = useState([])
  const [selectedTastingLogId, setSelectedTastingLogId] = useState('')
  const [tastingForm, setTastingForm] = useState(buildEmptyTastingForm())
  const [tastingMonth, setTastingMonth] = useState(new Date(new Date().getFullYear(), new Date().getMonth(), 1))
  const [tastingInsights, setTastingInsights] = useState(EMPTY_TASTING_INSIGHTS)
  const [availableIngredientsInput, setAvailableIngredientsInput] = useState('')
  const [minRecommendationScore, setMinRecommendationScore] = useState(25)
  const [aiProvider, setAiProvider] = useState('local')
  const [aiCocktailName, setAiCocktailName] = useState('')
  const [aiConstraints, setAiConstraints] = useState('')
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiSuggestions, setAiSuggestions] = useState([])
  const [aiNote, setAiNote] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [apiHealth, setApiHealth] = useState('checking')
  const [apiHealthMessage, setApiHealthMessage] = useState('Checking API connectivity...')
  const [lastRefreshedAt, setLastRefreshedAt] = useState('')
  const [successNotice, setSuccessNotice] = useState('')
  const [confirmDialog, setConfirmDialog] = useState({
    open: false,
    title: '',
    message: '',
    action: null
  })
  const [error, setError] = useState('')
  const [alcoholCountryFlagPath, setAlcoholCountryFlagPath] = useState('')
  const [alcoholTypeSuggestions, setAlcoholTypeSuggestions] = useState([])
  const [alcoholTypeSuggestionFamily, setAlcoholTypeSuggestionFamily] = useState('')
  const [alcoholWebLookupLoading, setAlcoholWebLookupLoading] = useState(false)
  const [storageSettings, setStorageSettings] = useState(EMPTY_STORAGE_SETTINGS)
  const [storageRootInput, setStorageRootInput] = useState('')
  const [storagePreflight, setStoragePreflight] = useState(null)
  const [storageApplyReport, setStorageApplyReport] = useState(null)
  const [storageLoading, setStorageLoading] = useState(false)
  const [storageApplying, setStorageApplying] = useState(false)
  const [storageMirroring, setStorageMirroring] = useState(false)
  const [backendRestarting, setBackendRestarting] = useState(false)
  const [editAccessPassword, setEditAccessPassword] = useState('')
  const [editUnlockTimestamp, setEditUnlockTimestamp] = useState(() => {
    try {
      const raw = window.sessionStorage.getItem(EDIT_UNLOCK_SESSION_KEY)
      const parsed = Number(raw || 0)
      return Number.isFinite(parsed) && parsed > 0 ? parsed : 0
    } catch (_err) {
      return 0
    }
  })
  const [lockClockTick, setLockClockTick] = useState(Date.now())

  const alcoholImageUrl = useMemo(() => {
    const sourcePath = alcoholEditorMode === 'view' ? selectedAlcohol?.image_path : alcoholForm.image_path
    return resolveImageUrl(sourcePath)
  }, [alcoholEditorMode, selectedAlcohol, alcoholForm.image_path])

  const cocktailImageUrl = useMemo(() => {
    const sourcePath = cocktailEditorMode === 'view' ? selectedCocktail?.image_path : cocktailForm.image_path
    return resolveImageUrl(sourcePath)
  }, [cocktailEditorMode, selectedCocktail, cocktailForm.image_path])

  const showSuccess = (message) => {
    setSuccessNotice(String(message || '').trim())
    window.setTimeout(() => {
      setSuccessNotice('')
    }, 2800)
  }

  const isEditUnlocked = editUnlockTimestamp > 0 && (lockClockTick - editUnlockTimestamp) < EDIT_UNLOCK_MAX_AGE_MS
  const remainingEditUnlockMs = isEditUnlocked ? Math.max(0, EDIT_UNLOCK_MAX_AGE_MS - (lockClockTick - editUnlockTimestamp)) : 0
  const remainingEditUnlockMinutes = Math.max(0, Math.ceil(remainingEditUnlockMs / 60000))

  const lockEditAccess = (showNotice = false) => {
    setEditUnlockTimestamp(0)
    setLockClockTick(Date.now())
    setEditAccessPassword('')
    if (showNotice) {
      showSuccess('Edit mode locked')
    }
  }

  const touchEditAccessActivity = () => {
    const now = Date.now()
    setEditUnlockTimestamp(now)
    setLockClockTick(now)
  }

  const ensureEditAccess = () => {
    if (!isEditUnlocked) {
      lockEditAccess(false)
      setError(EDIT_LOCKED_MESSAGE)
      return false
    }
    touchEditAccessActivity()
    return true
  }

  const withWriteLockIcon = (label) => (isEditUnlocked ? label : `🔒 ${label}`)

  const unlockEditAccess = () => {
    if (String(editAccessPassword || '').trim() !== EDIT_ACCESS_PASSWORD) {
      setError('Incorrect password. Enter the password in Settings to unlock edit actions.')
      return
    }
    touchEditAccessActivity()
    setEditAccessPassword('')
    setError('')
    showSuccess('Edit mode unlocked for this session')
  }

  const openConfirm = (title, message, action) => {
    setConfirmDialog({
      open: true,
      title: String(title || '').trim(),
      message: String(message || '').trim(),
      action: typeof action === 'function' ? action : null
    })
  }

  const closeConfirm = () => {
    setConfirmDialog({ open: false, title: '', message: '', action: null })
  }

  useEffect(() => {
    try {
      if (editUnlockTimestamp > 0) {
        window.sessionStorage.setItem(EDIT_UNLOCK_SESSION_KEY, String(editUnlockTimestamp))
      } else {
        window.sessionStorage.removeItem(EDIT_UNLOCK_SESSION_KEY)
      }
    } catch (_err) {
    }
  }, [editUnlockTimestamp])

  useEffect(() => {
    if (!isEditUnlocked) return undefined
    const intervalId = window.setInterval(() => {
      setLockClockTick(Date.now())
    }, 30000)
    return () => window.clearInterval(intervalId)
  }, [isEditUnlocked])

  useEffect(() => {
    if (!editUnlockTimestamp) return undefined
    const elapsed = Date.now() - editUnlockTimestamp
    const remaining = EDIT_UNLOCK_MAX_AGE_MS - elapsed
    if (remaining <= 0) {
      lockEditAccess(false)
      return undefined
    }
    const timeoutId = window.setTimeout(() => {
      lockEditAccess(false)
      setError('Edit mode auto-locked after 1 hour of inactivity.')
    }, remaining)
    return () => window.clearTimeout(timeoutId)
  }, [editUnlockTimestamp])

  const loadApiData = async (maxAttempts = 3) => {
    const attempts = Number.isFinite(maxAttempts) ? Math.max(1, Math.floor(maxAttempts)) : 3

    setLoading(true)
    setApiHealth('checking')
    setApiHealthMessage('Checking API connectivity...')

    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      try {
        const [countsResult, alcoholResult, cocktailsResult, tastingResult, savedViewsResult, costResult, tastingInsightsResult] = await Promise.allSettled([
          fetch(`${API_BASE}/meta/counts`),
          fetch(`${API_BASE}/alcohol?limit=500&offset=0`),
          fetch(`${API_BASE}/cocktails?limit=500&offset=0`),
          fetch(`${API_BASE}/tasting-logs`),
          fetch(`${API_BASE}/saved-views`),
          fetch(`${API_BASE}/analytics/cost-insights`),
          fetch(`${API_BASE}/analytics/tasting-insights`)
        ])

        const endpointFailures = []

        const resolveResponseJson = async (result, endpointName) => {
          if (result.status !== 'fulfilled') {
            endpointFailures.push(endpointName)
            return null
          }

          const response = result.value
          if (!response.ok) {
            endpointFailures.push(endpointName)
            return null
          }

          return response.json()
        }

        const countsJson = await resolveResponseJson(countsResult, 'meta/counts')
        const alcoholJson = await resolveResponseJson(alcoholResult, 'alcohol')
        const cocktailsJson = await resolveResponseJson(cocktailsResult, 'cocktails')
        const tastingJson = await resolveResponseJson(tastingResult, 'tasting-logs')
        const savedViewsJson = await resolveResponseJson(savedViewsResult, 'saved-views')
        const costJson = await resolveResponseJson(costResult, 'analytics/cost-insights')
        const tastingInsightsJson = await resolveResponseJson(tastingInsightsResult, 'analytics/tasting-insights')

        const alcoholItems = alcoholJson?.items || []
        const cocktailItems = cocktailsJson?.items || []

        if (!alcoholItems.length && !cocktailItems.length) {
          throw new Error('Failed to load core record endpoints (alcohol/cocktails).')
        }

        setCounts(countsJson || {
          alcohol_inventory: alcoholItems.length,
          cocktail_notes: cocktailItems.length
        })
        setAlcohol(alcoholItems)
        setCocktails(cocktailItems)
        setTastingLogs(((tastingJson && tastingJson.items) || []).map(normalizeTastingItem))
        setSavedViews(((savedViewsJson && savedViewsJson.items) || []).map(normalizeSavedView))
        setCostInsights(costJson || EMPTY_COST_INSIGHTS)
        setTastingInsights(tastingInsightsJson || EMPTY_TASTING_INSIGHTS)
        setSelectedAlcohol(alcoholItems[0] || null)
        setSelectedCocktail(cocktailItems[0] || null)

        if (endpointFailures.length) {
          setError(`Partial data loaded. Unavailable: ${endpointFailures.join(', ')}`)
          setApiHealth('degraded')
          setApiHealthMessage(`Partial API availability (${endpointFailures.join(', ')})`)
        } else {
          setError('')
          setApiHealth('healthy')
          setApiHealthMessage('All API endpoints are reachable')
        }
        setLastRefreshedAt(new Date().toISOString())

        setLoading(false)
        return
      } catch (e) {
        const message = e.message || 'API unreachable'
        if (attempt < attempts) {
          const waitSeconds = attempt
          setApiHealth('checking')
          setApiHealthMessage(`Retrying API in ${waitSeconds}s (attempt ${attempt + 1}/${attempts})...`)
          await wait(waitSeconds * 1000)
          continue
        }

        setError(message)
        setApiHealth('offline')
        setApiHealthMessage(message)
      }
    }

    setLoading(false)
  }

  const loadStorageSettings = async (preserveRootInput = false) => {
    try {
      const res = await fetch(`${API_BASE}/settings/storage`)
      const payload = await res.json()
      if (!res.ok) {
        throw new Error(payload?.detail || 'Failed to load storage settings')
      }
      setStorageSettings(payload || EMPTY_STORAGE_SETTINGS)
      if (!preserveRootInput) {
        setStorageRootInput(String(payload?.root_path || '').trim())
      }
    } catch (e) {
      setError(e.message || 'Failed to load storage settings')
    }
  }

  const browseStorageFolder = async () => {
    setStorageLoading(true)
    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => controller.abort(), 190000)
    try {
      const res = await fetch(`${API_BASE}/settings/storage/browse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initial_path: storageRootInput || storageSettings.root_path || '' }),
        signal: controller.signal
      })
      const payload = await res.json()
      if (!res.ok) {
        throw new Error(payload?.detail || 'Failed to browse for folder')
      }
      const selectedPath = String(payload?.selected_path || '').trim()
      if (!selectedPath) return
      setStorageRootInput(selectedPath)
      setStoragePreflight(null)
      setStorageApplyReport(null)
      setError('')
    } catch (e) {
      if (e.name === 'AbortError') {
        setError('Folder picker timed out or was blocked. Please try again.')
      } else {
        setError(e.message || 'Failed to browse for folder')
      }
    } finally {
      window.clearTimeout(timeoutId)
      setStorageLoading(false)
    }
  }

  const runStoragePreflight = async (rootPathOverride) => {
    const rootPath = String(rootPathOverride ?? (storageRootInput || '')).trim()
    if (!rootPath) {
      setError('Select a storage root folder first.')
      return
    }
    setStorageLoading(true)
    try {
      const res = await fetch(`${API_BASE}/settings/storage/preflight`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ root_path: rootPath })
      })
      const payload = await res.json()
      if (!res.ok) {
        throw new Error(payload?.detail || 'Failed to run storage preflight')
      }
      setStoragePreflight(payload)
      setStorageApplyReport(null)
      setError('')
    } catch (e) {
      setError(e.message || 'Failed to run storage preflight')
    } finally {
      setStorageLoading(false)
    }
  }

  const waitForApiRecovery = async (maxAttempts = 45) => {
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      try {
        const res = await fetch(`${API_BASE}/health`)
        if (res.ok) {
          return true
        }
      } catch (_err) {
      }
      await wait(1000)
    }
    return false
  }

  const applyStorageSettings = async () => {
    if (!ensureEditAccess()) return

    const rootPath = String(storageRootInput || '').trim()
    if (!rootPath) {
      setError('Select a storage root folder first.')
      return
    }

    setStorageApplying(true)
    setBackendRestarting(true)
    try {
      const res = await fetch(`${API_BASE}/settings/storage/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ root_path: rootPath })
      })
      let payload = null
      try {
        payload = await res.json()
      } catch (_err) {
        payload = null
      }

      if (res.ok) {
        setStorageApplyReport(payload)
        setStoragePreflight(null)
      }
      if (!res.ok) {
        throw new Error(payload?.detail || 'Failed to apply storage settings')
      }

      setError('Applying storage settings and restarting backend...')

      await wait(2500)
      const recovered = await waitForApiRecovery()
      if (!recovered) {
        throw new Error('Backend restart did not recover in time. Please retry connection.')
      }

      await loadApiData()
      await loadStorageSettings()
      await runStoragePreflight(rootPath)
      setError('')
      showSuccess('Storage settings applied')
      setBackendRestarting(false)
    } catch (e) {
      const message = String(e?.message || '')
      if (
        message.includes('Failed to fetch') ||
        message.includes('NetworkError') ||
        message.includes('Load failed')
      ) {
        setError('Apply request interrupted by backend restart. Waiting for reconnect...')
        const recovered = await waitForApiRecovery()
        if (recovered) {
          await loadApiData()
          await loadStorageSettings()
          await runStoragePreflight(rootPath)
          setError('')
          setBackendRestarting(false)
          return
        }
      }
      setError(message || 'Failed to apply storage settings')
      setBackendRestarting(false)
    } finally {
      setStorageApplying(false)
    }
  }

  const mirrorStorageNow = async () => {
    if (!ensureEditAccess()) return

    setStorageMirroring(true)
    try {
      const res = await fetch(`${API_BASE}/settings/storage/mirror-now`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })
      const payload = await res.json()
      if (!res.ok) {
        throw new Error(payload?.detail || 'Failed to run mirror now')
      }

      await loadStorageSettings()
      setError('')
      showSuccess('Mirror complete')
    } catch (e) {
      setError(e.message || 'Failed to run mirror now')
    } finally {
      setStorageMirroring(false)
    }
  }

  useEffect(() => {
    loadApiData()
    loadStorageSettings()
  }, [])

  useEffect(() => {
    if (activeTab !== 'alcohol') return
    if (!selectedAlcohol) {
      setAlcoholForm(EMPTY_ALCOHOL_FORM)
      return
    }
    setAlcoholForm(mapAlcoholRowToForm(selectedAlcohol))
  }, [selectedAlcohol, activeTab])

  useEffect(() => {
    if (activeTab !== 'cocktails') return
    if (!selectedCocktail) {
      setCocktailForm(EMPTY_COCKTAIL_FORM)
      return
    }
    setCocktailForm(mapCocktailRowToForm(selectedCocktail))
  }, [selectedCocktail, activeTab])

  useEffect(() => {
    const country = String(selectedAlcohol?.Country || '').trim()
    if (!country) {
      setAlcoholCountryFlagPath('')
      return
    }

    let cancelled = false

    const loadCountryFlag = async () => {
      try {
        const res = await fetch(`${API_BASE}/meta/flag-by-country?country=${encodeURIComponent(country)}`)
        if (!res.ok) {
          throw new Error('Failed to resolve country flag')
        }
        const data = await res.json()
        if (!cancelled) {
          setAlcoholCountryFlagPath(String(data.image_path || '').trim())
        }
      } catch (_err) {
        if (!cancelled) {
          setAlcoholCountryFlagPath('')
        }
      }
    }

    loadCountryFlag()

    return () => {
      cancelled = true
    }
  }, [selectedAlcohol?.Country])

  const filteredAlcohol = useMemo(() => {
    const q = query.trim().toLowerCase()
    return alcohol.filter((row) => {
      const matchesSearch = !q ||
        [row.Brand, row.Base_Liquor, row.Type, row.Country, row.Availability]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
          .includes(q)

      const matchesBaseLiquor =
        alcoholBaseLiquorFilter === 'all' || row.Base_Liquor === alcoholBaseLiquorFilter

      const matchesAvailability =
        alcoholAvailabilityFilter === 'all' || row.Availability === alcoholAvailabilityFilter

      return matchesSearch && matchesBaseLiquor && matchesAvailability
    })
  }, [
    alcohol,
    query,
    alcoholBaseLiquorFilter,
    alcoholAvailabilityFilter
  ])

  const filteredCocktails = useMemo(() => {
    const q = query.trim().toLowerCase()
    const minRating = cocktailMinRatingFilter === '' ? null : Number(cocktailMinRatingFilter)

    return cocktails.filter((row) => {
      const matchesSearch = !q ||
        [row.Cocktail_Name, row.Base_spirit_1, row.Brand1, row.Ingredients]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
          .includes(q)

      const matchesBaseSpirit =
        cocktailBaseSpiritFilter === 'all' || row.Base_spirit_1 === cocktailBaseSpiritFilter

      const rating = Number(row.Rating_overall)
      const matchesMinRating =
        minRating === null || (!Number.isNaN(rating) && rating >= minRating)

      const difficulty = Number(row.Difficulty)
      const matchesDifficulty =
        cocktailMaxDifficultyFilter === 'all' ||
        (!Number.isNaN(difficulty) && difficulty === Number(cocktailMaxDifficultyFilter))

      return matchesSearch && matchesBaseSpirit && matchesMinRating && matchesDifficulty
    })
  }, [
    cocktails,
    query,
    cocktailBaseSpiritFilter,
    cocktailMinRatingFilter,
    cocktailMaxDifficultyFilter
  ])

  const alcoholBaseLiquorOptions = useMemo(() => {
    const values = [...new Set(alcohol.map((row) => row.Base_Liquor).filter(Boolean))]
    return values.sort((a, b) => a.localeCompare(b))
  }, [alcohol])

  const alcoholAvailabilityOptions = useMemo(() => {
    const values = [...new Set(alcohol.map((row) => row.Availability).filter(Boolean))]
    return values.sort((a, b) => a.localeCompare(b))
  }, [alcohol])

  const cocktailBaseSpiritOptions = useMemo(() => {
    const values = [...new Set(cocktails.map((row) => row.Base_spirit_1).filter(Boolean))]
    return values.sort((a, b) => a.localeCompare(b))
  }, [cocktails])

  const tastingLogsSorted = useMemo(() => {
    return [...tastingLogs].sort((a, b) => {
      const left = `${a.date || ''}-${a.createdAt || ''}`
      const right = `${b.date || ''}-${b.createdAt || ''}`
      return right.localeCompare(left)
    })
  }, [tastingLogs])

  const tastingMonthLabel = useMemo(
    () => tastingMonth.toLocaleString(undefined, { month: 'long', year: 'numeric' }),
    [tastingMonth]
  )

  const tastingMonthSummary = useMemo(() => {
    const monthPrefix = `${tastingMonth.getFullYear()}-${String(tastingMonth.getMonth() + 1).padStart(2, '0')}`
    const rows = tastingLogs.filter((entry) => (entry.date || '').startsWith(monthPrefix))
    const numericRatings = rows.map((entry) => Number(entry.rating)).filter((v) => !Number.isNaN(v))
    const avgRating = numericRatings.length
      ? (numericRatings.reduce((sum, val) => sum + val, 0) / numericRatings.length).toFixed(1)
      : '-'
    return { count: rows.length, avgRating }
  }, [tastingLogs, tastingMonth])

  const cocktailCostLookup = useMemo(() => {
    const pairs = (costInsights.cocktail_estimated_costs || []).map((row) => [
      normalizeNameKey(row.cocktail_name),
      row.estimated_cost_nzd
    ])
    return new Map(pairs.filter((item) => item[0]))
  }, [costInsights.cocktail_estimated_costs])

  const spiritAvgPriceLookup = useMemo(() => {
    const pairs = (costInsights.base_spirit_avg_price || []).map((row) => [
      normalizeNameKey(row.base_spirit),
      Number(row.avg_price_nzd)
    ])
    return new Map(pairs.filter((item) => item[0] && !Number.isNaN(item[1])))
  }, [costInsights.base_spirit_avg_price])

  const selectedTastingLog = useMemo(() => {
    if (!selectedTastingLogId) return tastingLogsSorted[0] || null
    return tastingLogsSorted.find((entry) => entry.id === selectedTastingLogId) || tastingLogsSorted[0] || null
  }, [selectedTastingLogId, tastingLogsSorted])

  const selectedTastingCost = useMemo(() => {
    const cocktailName = String(selectedTastingLog?.cocktailName || '').trim()
    if (!cocktailName) return null

    const direct = cocktailCostLookup.get(normalizeNameKey(cocktailName))
    if (direct !== undefined && direct !== null) {
      return Number(direct)
    }

    const cocktailRow = cocktails.find(
      (row) => normalizeNameKey(row.Cocktail_Name) === normalizeNameKey(cocktailName)
    )
    if (!cocktailRow) return null

    const spirit1 = normalizeNameKey(cocktailRow.Base_spirit_1)
    const spirit2 = normalizeNameKey(cocktailRow.Base_spirit_2)
    const p1 = spirit1 ? spiritAvgPriceLookup.get(spirit1) : null
    const p2 = spirit2 ? spiritAvgPriceLookup.get(spirit2) : null

    if (p1 != null && p2 != null) {
      return (p1 * (30 / 700)) + (p2 * (30 / 700))
    }
    if (p1 != null) {
      return p1 * (60 / 700)
    }
    if (p2 != null) {
      return p2 * (60 / 700)
    }
    return null
  }, [selectedTastingLog, cocktailCostLookup, cocktails, spiritAvgPriceLookup])

  const selectedTastingCostDisplay = useMemo(() => {
    if (selectedTastingCost == null || Number.isNaN(Number(selectedTastingCost))) return '-'
    return `${Number(selectedTastingCost).toFixed(2)} NZD`
  }, [selectedTastingCost])

  const selectedTastingRatingStars = useMemo(() => {
    const rawRating = Number(selectedTastingLog?.rating)
    if (Number.isNaN(rawRating) || rawRating <= 0) {
      return null
    }

    const clamped = Math.max(0, Math.min(MAX_SCORE, rawRating))
    const roundedScore = Math.round(clamped * 10) / 10
    const fillPercent = (roundedScore / MAX_SCORE) * 100
    return {
      roundedScore,
      fillPercent,
      score: `${formatNumericString(clamped)} out of 5`
    }
  }, [selectedTastingLog])

  const selectedTastingDetailRows = useMemo(() => {
    if (!selectedTastingLog) return []

    const rows = []
    const dateValue = formatDateTime(selectedTastingLog.date)
    if (dateValue && dateValue !== '-') {
      rows.push({ label: 'Date & Time', value: dateValue })
    }

    const cocktailName = String(selectedTastingLog.cocktailName || '').trim()
    if (cocktailName) {
      rows.push({ label: 'Cocktail', value: cocktailName })
    }

    if (selectedTastingCostDisplay !== '-') {
      rows.push({ label: 'Est. Cost to Make', value: selectedTastingCostDisplay })
    }

    const optionalFields = [
      ['Mood', selectedTastingLog.mood],
      ['Occasion', selectedTastingLog.occasion],
      ['Location', selectedTastingLog.location],
      ['Make Again', selectedTastingLog.wouldMakeAgain],
      ['Change Next Time', selectedTastingLog.changeNextTime],
      ['Notes', selectedTastingLog.notes]
    ]

    optionalFields.forEach(([label, value]) => {
      const text = String(value || '').trim()
      if (text) {
        rows.push({ label, value: text })
      }
    })

    return rows
  }, [selectedTastingLog, selectedTastingCostDisplay])

  const selectedTastingFlavorRows = useMemo(() => {
    if (!selectedTastingLog) return []

    return TASTING_DIMENSIONS
      .map((dimension) => {
        const raw = selectedTastingLog[dimension.key]
        if (raw === null || raw === undefined || String(raw).trim() === '') {
          return null
        }
        const numeric = Number(raw)
        if (Number.isNaN(numeric)) {
          return null
        }
        const value = Math.max(0, Math.min(10, numeric))
        return {
          key: dimension.key,
          label: dimension.label,
          value,
          percent: value * 10
        }
      })
      .filter(Boolean)
  }, [selectedTastingLog])

  const wouldMakeAgainDisplay = useMemo(() => {
    const value = tastingInsights.would_make_again_rate_pct
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return '-'
    }
    return `${Number(value).toFixed(1)}%`
  }, [tastingInsights.would_make_again_rate_pct])

  const recommendationResults = useMemo(() => {
    const userTokens = new Set(parseIngredientText(availableIngredientsInput))

    const availableBaseSpirits = new Set(
      alcohol
        .filter((row) => {
          const value = String(row.Availability || '').toLowerCase()
          return value !== 'no' && value !== 'unavailable'
        })
        .map((row) => String(row.Base_Liquor || '').toLowerCase().trim())
        .filter(Boolean)
    )

    return cocktails
      .map((row) => {
        const ingredientTokens = [...new Set(parseIngredientText(row.Ingredients || ''))]
        const matchedIngredients = ingredientTokens.filter((token) => {
          if (userTokens.has(token)) return true
          for (const userToken of userTokens) {
            if (token.includes(userToken) || userToken.includes(token)) return true
          }
          return false
        })

        const missingIngredients = ingredientTokens.filter((token) => !matchedIngredients.includes(token))
        const ingredientCoverage = ingredientTokens.length
          ? matchedIngredients.length / ingredientTokens.length
          : 0

        const baseSpirit = String(row.Base_spirit_1 || '').toLowerCase().trim()
        const hasBaseSpirit = baseSpirit ? availableBaseSpirits.has(baseSpirit) : false
        const baseSpiritBonus = hasBaseSpirit ? 10 : 0

        const rating = Number(row.Rating_overall)
        const ratingBonus = Number.isNaN(rating) ? 0 : Math.max(0, Math.min(MAX_SCORE, rating)) * 4

        const score = Math.round(ingredientCoverage * 70 + ratingBonus + baseSpiritBonus)

        return {
          cocktailName: row.Cocktail_Name,
          score,
          matchedCount: matchedIngredients.length,
          totalCount: ingredientTokens.length,
          missingIngredients,
          hasBaseSpirit,
          baseSpirit: row.Base_spirit_1 || '-',
          difficulty: row.Difficulty || '-',
          rating: row.Rating_overall || '-'
        }
      })
      .filter((row) => row.score >= minRecommendationScore)
      .sort((a, b) => b.score - a.score)
      .slice(0, 25)
  }, [availableIngredientsInput, alcohol, cocktails, minRecommendationScore])

  const analyticsSummary = useMemo(() => {
    const rated = cocktails
      .map((row) => Number(row.Rating_overall))
      .filter((value) => !Number.isNaN(value))
    const avgCocktailRating = rated.length
      ? (rated.reduce((sum, value) => sum + value, 0) / rated.length).toFixed(1)
      : '-'

    const availableAlcoholCount = alcohol.filter((row) => {
      const value = String(row.Availability || '').toLowerCase()
      return value !== 'no' && value !== 'unavailable'
    }).length

    const difficultyBuckets = { '1-2': 0, '3': 0, '4-5': 0 }
    cocktails.forEach((row) => {
      const diff = Number(row.Difficulty)
      if (Number.isNaN(diff)) return
      if (diff <= 2) difficultyBuckets['1-2'] += 1
      else if (diff === 3) difficultyBuckets['3'] += 1
      else difficultyBuckets['4-5'] += 1
    })

    return {
      totalAlcohol: alcohol.length,
      totalCocktails: cocktails.length,
      avgCocktailRating,
      availableAlcoholCount,
      tastingCount: tastingLogs.length,
      difficultyBuckets
    }
  }, [alcohol, cocktails, tastingLogs])

  const spiritUsage = useMemo(() => {
    const counts = {}
    cocktails.forEach((row) => {
      const spirit = (row.Base_spirit_1 || 'Unknown').trim()
      counts[spirit] = (counts[spirit] || 0) + 1
    })

    const entries = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)

    const max = entries.length ? entries[0][1] : 1
    return entries.map(([name, count]) => ({ name, count, pct: Math.round((count / max) * 100) }))
  }, [cocktails])

  const ratingTrend = useMemo(() => {
    const sorted = [...tastingLogs]
      .filter((entry) => !Number.isNaN(Number(entry.rating)))
      .sort((a, b) => String(a.date || '').localeCompare(String(b.date || '')))

    const monthly = {}
    sorted.forEach((entry) => {
      const key = String(entry.date || '').slice(0, 7)
      if (!key) return
      if (!monthly[key]) monthly[key] = []
      monthly[key].push(Number(entry.rating))
    })

    return Object.entries(monthly)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .slice(-6)
      .map(([month, values]) => {
        const avg = values.reduce((sum, v) => sum + v, 0) / values.length
        return { month, avg: avg.toFixed(1) }
      })
  }, [tastingLogs])

  const libraryOverviewCards = useMemo(() => {
    return [
      { key: 'bottles', label: 'Bottles', value: analyticsSummary.totalAlcohol },
      { key: 'recipes', label: 'Recipes', value: analyticsSummary.totalCocktails },
      { key: 'available', label: 'Available Now', value: analyticsSummary.availableAlcoholCount },
      { key: 'avg-rating', label: 'Avg Cocktail Rating', value: analyticsSummary.avgCocktailRating },
      { key: 'tastings', label: 'Tasting Entries', value: analyticsSummary.tastingCount },
      { key: 'make-again', label: 'Would Make Again', value: wouldMakeAgainDisplay }
    ]
  }, [analyticsSummary, wouldMakeAgainDisplay])

  const ratingTrendChartData = useMemo(() => {
    return ratingTrend
      .map((row) => ({ month: formatShortMonth(row.month), avg: Number(row.avg) }))
      .filter((row) => !Number.isNaN(row.avg))
  }, [ratingTrend])

  const difficultyMixChartData = useMemo(() => {
    return [
      { name: 'Easy (1-2)', value: analyticsSummary.difficultyBuckets['1-2'] || 0 },
      { name: 'Medium (3)', value: analyticsSummary.difficultyBuckets['3'] || 0 },
      { name: 'Advanced (4-5)', value: analyticsSummary.difficultyBuckets['4-5'] || 0 }
    ].filter((row) => row.value > 0)
  }, [analyticsSummary])

  const moodBreakdownChartData = useMemo(() => {
    return (tastingInsights.mood_breakdown || [])
      .map((row) => ({ name: row.mood || 'Unspecified', value: Number(row.count || 0) }))
      .filter((row) => row.value > 0)
  }, [tastingInsights.mood_breakdown])

  const topCocktailsChartData = useMemo(() => {
    return (tastingInsights.top_cocktails || [])
      .slice(0, 6)
      .map((row) => ({ name: String(row.name || '-').slice(0, 18), entries: Number(row.entries || 0) }))
      .filter((row) => row.entries > 0)
  }, [tastingInsights.top_cocktails])

  const spiritRatingChartData = useMemo(() => {
    return (tastingInsights.rating_by_base_spirit || [])
      .slice(0, 8)
      .map((row) => ({ name: row.base_spirit || 'Unknown', avg: Number(row.avg_rating || 0) }))
      .filter((row) => !Number.isNaN(row.avg) && row.avg > 0)
  }, [tastingInsights.rating_by_base_spirit])

  const flavorProfileChartData = useMemo(() => {
    return (tastingInsights.flavor_profile_avg || [])
      .map((row) => ({ dimension: prettyLabel(row.dimension), avg: Number(row.avg || 0) }))
      .filter((row) => !Number.isNaN(row.avg) && row.avg > 0)
  }, [tastingInsights.flavor_profile_avg])

  const monthlyCostChartData = useMemo(() => {
    return (costInsights.tasting_monthly_estimated_cost || [])
      .slice(-8)
      .map((row) => ({ month: formatShortMonth(row.month), total: Number(row.total_estimated_cost_nzd || 0) }))
      .filter((row) => !Number.isNaN(row.total))
  }, [costInsights.tasting_monthly_estimated_cost])

  const makeAgainChartData = useMemo(() => {
    const pct = Number(tastingInsights.would_make_again_rate_pct)
    if (Number.isNaN(pct) || pct < 0) return []
    const yes = Math.max(0, Math.min(100, pct))
    return [
      { name: 'Yes', value: yes },
      { name: 'No', value: Math.max(0, 100 - yes) }
    ]
  }, [tastingInsights.would_make_again_rate_pct])

  const tastingCalendarDays = useMemo(() => {
    const year = tastingMonth.getFullYear()
    const month = tastingMonth.getMonth()
    const monthStart = new Date(year, month, 1)
    const firstDay = monthStart.getDay()
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const monthPrefix = `${year}-${String(month + 1).padStart(2, '0')}`

    const dayCounts = {}
    tastingLogs.forEach((entry) => {
      if (!entry.date || !entry.date.startsWith(monthPrefix)) return
      const day = Number(entry.date.slice(8, 10))
      if (Number.isNaN(day)) return
      dayCounts[day] = (dayCounts[day] || 0) + 1
    })

    const days = []
    for (let i = 0; i < firstDay; i += 1) {
      days.push({ empty: true, key: `empty-${i}` })
    }
    for (let day = 1; day <= daysInMonth; day += 1) {
      days.push({
        empty: false,
        key: `day-${day}`,
        day,
        count: dayCounts[day] || 0
      })
    }
    return days
  }, [tastingLogs, tastingMonth])

  const saveCurrentView = async () => {
    const trimmedName = viewName.trim()
    if (!trimmedName) {
      return
    }

    const payload = {
      id: `${Date.now()}`,
      name: trimmedName,
      tab: activeTab,
      query,
      filters:
        activeTab === 'alcohol'
          ? {
              alcoholBaseLiquorFilter,
              alcoholAvailabilityFilter
            }
          : {
              cocktailBaseSpiritFilter,
              cocktailMinRatingFilter,
              cocktailMaxDifficultyFilter
            }
    }

    try {
      const res = await fetch(`${API_BASE}/saved-views`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: trimmedName,
          payload: {
            tab: payload.tab,
            query: payload.query,
            filters: payload.filters
          }
        })
      })

      if (!res.ok) {
        throw new Error('Failed to save view')
      }

      const created = await res.json()
      setSavedViews((prev) => [normalizeSavedView(created), ...prev].slice(0, 20))
      setViewName('')
      await loadStorageSettings(true)
      showSuccess('Saved view created')
    } catch (e) {
      setError(e.message || 'Failed to save view')
    }
  }

  const applySavedView = (view) => {
    setActiveTab(view.tab)
    setQuery(view.query || '')

    if (view.tab === 'alcohol') {
      setAlcoholBaseLiquorFilter(view.filters?.alcoholBaseLiquorFilter || 'all')
      setAlcoholAvailabilityFilter(view.filters?.alcoholAvailabilityFilter || 'all')
    } else {
      setCocktailBaseSpiritFilter(view.filters?.cocktailBaseSpiritFilter || 'all')
      setCocktailMinRatingFilter(view.filters?.cocktailMinRatingFilter || '')
      setCocktailMaxDifficultyFilter(view.filters?.cocktailMaxDifficultyFilter || 'all')
    }
  }

  const updateCocktailFormField = (key, value) => {
    if (FIVE_SCALE_FIELDS.has(key)) {
      const normalized = normalizeFiveScaleInput(value)
      if (normalized === null) return
      setCocktailForm((prev) => ({ ...prev, [key]: normalized }))
      return
    }
    setCocktailForm((prev) => ({ ...prev, [key]: value }))
  }

  const updateTastingRatingField = (value) => {
    const normalized = normalizeFiveScaleInput(value)
    if (normalized === null) return
    setTastingForm((prev) => ({ ...prev, rating: normalized }))
  }

  const updateCocktailMinRatingFilter = (value) => {
    const normalized = normalizeFiveScaleInput(value)
    if (normalized === null) return
    setCocktailMinRatingFilter(normalized)
  }

  const finalizeAlcoholFormattedField = (key) => {
    setAlcoholForm((prev) => {
      if (key === 'ABV') {
        return { ...prev, ABV: normalizeAbvValue(prev.ABV) }
      }
      if (key === 'Price_NZD_700ml') {
        return { ...prev, Price_NZD_700ml: normalizePriceValue(prev.Price_NZD_700ml) }
      }
      return prev
    })
  }

  const resetCocktailForm = () => {
    setSelectedCocktail(null)
    setCocktailForm(EMPTY_COCKTAIL_FORM)
    setCocktailEditorMode('view')
  }

  const startCreateCocktail = () => {
    if (!ensureEditAccess()) return

    setSelectedCocktail(null)
    setCocktailForm({ ...EMPTY_COCKTAIL_FORM, image_path: 'images/cocktails/' })
    setCocktailEditorMode('create')
  }

  const startEditCocktail = () => {
    if (!ensureEditAccess()) return

    if (!selectedCocktail?._rowid) {
      setError('Select a cocktail row before updating')
      return
    }
    setCocktailForm(mapCocktailRowToForm(selectedCocktail))
    setCocktailEditorMode('edit')
    setError('')
  }

  const lookupAlcoholWebHints = async () => {
    const brand = String(alcoholForm.Brand || '').trim()
    const baseLiquor = String(alcoholForm.Base_Liquor || '').trim()
    const alcoholType = String(alcoholForm.Type || '').trim()

    if (!brand) {
      setError('Brand is required before web lookup.')
      return
    }

    setAlcoholWebLookupLoading(true)
    try {
      const params = new URLSearchParams({ brand })
      if (baseLiquor) params.set('base_liquor', baseLiquor)
      if (alcoholType) params.set('type', alcoholType)

      const res = await fetch(`${API_BASE}/alcohol-web-hints?${params.toString()}`)
      const payload = await res.json()
      if (!res.ok) {
        throw new Error(payload?.detail || 'Failed to fetch web hints')
      }

      const suggestedTypes = Array.isArray(payload?.suggested_types)
        ? payload.suggested_types.map((item) => String(item || '').trim()).filter(Boolean)
        : []

      const nextABV = String(payload?.abv_hint || '').trim()
      const nextCountry = String(payload?.country_hint || '').trim()
      const nextPrice = String(payload?.price_nzd_hint || '').trim()
      const nextSubstitute = String(payload?.substitute_hint || '').trim()
      const nextTaste = String(payload?.taste_hint || '').trim()
      const tastePrefix = [brand, alcoholType || baseLiquor].filter(Boolean).join(' · ')
      const formattedTaste = nextTaste ? `${tastePrefix}: ${nextTaste}` : ''

      setAlcoholForm((prev) => ({
        ...prev,
        ABV: nextABV || String(prev.ABV || '').trim(),
        Country: nextCountry || String(prev.Country || '').trim(),
        Price_NZD_700ml: nextPrice || String(prev.Price_NZD_700ml || '').trim(),
        Substitute: nextSubstitute || String(prev.Substitute || '').trim(),
        Taste: formattedTaste || String(prev.Taste || '').trim()
      }))

      if (suggestedTypes.length > 0) {
        setAlcoholTypeSuggestions((prev) => [...new Set([...suggestedTypes, ...prev])])
        setAlcoholTypeSuggestionFamily(baseFamilyFromBaseLiquor(baseLiquor))
        if (!String(alcoholForm.Type || '').trim()) {
          setAlcoholForm((prev) => ({ ...prev, Type: suggestedTypes[0] }))
        }
      }

      setError('')
    } catch (e) {
      setError(e.message || 'Failed to fetch web hints')
    } finally {
      setAlcoholWebLookupLoading(false)
    }
  }

  const prefillAlcoholDetails = () => {
    const brand = String(alcoholForm.Brand || '').trim()
    if (!brand) {
      setError('Brand is required before pre-filling details.')
      return
    }

    const source = findBestAlcoholPrefillSource(alcohol, alcoholForm)
    if (!source) {
      setError('No matching alcohol record found to pre-fill details.')
      return
    }

    setAlcoholForm((prev) => ({
      ...prev,
      Country: String(prev.Country || '').trim() || String(source.Country || '').trim(),
      Price_NZD_700ml: String(prev.Price_NZD_700ml || '').trim() || String(source.Price_NZD_700ml || '').trim(),
      ABV: String(prev.ABV || '').trim() || String(source.ABV || '').trim(),
      Substitute: String(prev.Substitute || '').trim() || String(source.Substitute || '').trim()
    }))
    setError('')
  }

  const cancelCocktailEdit = () => {
    if (selectedCocktail?._rowid) {
      setCocktailForm(mapCocktailRowToForm(selectedCocktail))
    } else {
      setCocktailForm(EMPTY_COCKTAIL_FORM)
    }
    setCocktailEditorMode('view')
  }

  const saveCocktailForm = async () => {
    if (!ensureEditAccess()) return

    if (!cocktailForm.Cocktail_Name.trim()) {
      setError('Cocktail name is required')
      return
    }

    for (const [key, label] of [
      ['Rating_Jason', 'Jason rating'],
      ['Rating_Jaime', 'Jaime rating'],
      ['Rating_overall', 'Overall rating'],
      ['Difficulty', 'Difficulty']
    ]) {
      if (!isValidFiveScaleValue(cocktailForm[key])) {
        setError(`${label} must be between 0 and 5 (decimals allowed).`)
        return
      }
    }

    try {
      const payload = {
        ...cocktailForm,
        Rating_Jason: formatNumericString(cocktailForm.Rating_Jason || ''),
        Rating_Jaime: formatNumericString(cocktailForm.Rating_Jaime || ''),
        Rating_overall: formatNumericString(cocktailForm.Rating_overall || ''),
        Difficulty: formatNumericString(cocktailForm.Difficulty || '')
      }
      const hasRowId = Boolean(selectedCocktail?._rowid)
      const url = hasRowId
        ? `${API_BASE}/cocktails/id/${selectedCocktail._rowid}`
        : `${API_BASE}/cocktails`
      const method = hasRowId ? 'PUT' : 'POST'

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        throw new Error(hasRowId ? 'Failed to update cocktail record' : 'Failed to create cocktail record')
      }

      const data = await res.json()
      const item = data.item

      setCocktails((prev) => {
        if (hasRowId) {
          return prev.map((row) => (row._rowid === item._rowid ? item : row))
        }
        return [item, ...prev]
      })

      setCounts((prev) => {
        const current = prev || { alcohol_inventory: alcohol.length, cocktail_notes: 0 }
        return {
          ...current,
          cocktail_notes: hasRowId ? current.cocktail_notes : current.cocktail_notes + 1
        }
      })

      setSelectedCocktail(item)
      setCocktailForm(mapCocktailRowToForm(item))
      setCocktailEditorMode('view')
      await loadStorageSettings(true)
      setError('')
      showSuccess(hasRowId ? 'Cocktail updated' : 'Cocktail created')
    } catch (e) {
      setError(e.message || 'Failed to save cocktail record')
    }
  }

  const deleteSelectedCocktail = async () => {
    if (!ensureEditAccess()) return

    const rowId = selectedCocktail?._rowid
    if (!rowId) return

    const cocktailName = selectedCocktail?.Cocktail_Name || 'this cocktail'
    openConfirm(
      'Delete Cocktail',
      `This will permanently delete "${cocktailName}". Continue?`,
      async () => {
        if (!ensureEditAccess()) return

        try {
          const res = await fetch(`${API_BASE}/cocktails/id/${rowId}`, { method: 'DELETE' })
          if (!res.ok) {
            throw new Error('Failed to delete cocktail record')
          }

          setCocktails((prev) => prev.filter((row) => row._rowid !== rowId))
          setCounts((prev) => {
            const current = prev || { alcohol_inventory: alcohol.length, cocktail_notes: 0 }
            return {
              ...current,
              cocktail_notes: Math.max(0, current.cocktail_notes - 1)
            }
          })
          resetCocktailForm()
          await loadStorageSettings(true)
          setError('')
          showSuccess('Cocktail deleted')
        } catch (e) {
          setError(e.message || 'Failed to delete cocktail record')
        }
      }
    )
  }

  const removeSavedView = async (id) => {
    const targetView = savedViews.find((item) => item.id === id)
    openConfirm(
      'Delete Saved View',
      `Delete saved view "${targetView?.name || 'this view'}"?`,
      async () => {
        try {
          const res = await fetch(`${API_BASE}/saved-views/${id}`, { method: 'DELETE' })
          if (!res.ok) {
            throw new Error('Failed to delete view')
          }
          setSavedViews((prev) => prev.filter((item) => item.id !== id))
          await loadStorageSettings(true)
          showSuccess('Saved view removed')
        } catch (e) {
          setError(e.message || 'Failed to delete view')
        }
      }
    )
  }

  const updateAlcoholFormField = (key, value) => {
    if (key === 'Brand' || key === 'Base_Liquor') {
      setAlcoholTypeSuggestions([])
      setAlcoholTypeSuggestionFamily('')
    }
    setAlcoholForm((prev) => ({ ...prev, [key]: value }))
  }

  const suggestAlcoholType = () => {
    const brand = String(alcoholForm.Brand || '').trim()
    const baseLiquor = String(alcoholForm.Base_Liquor || '').trim()
    if (!brand || !baseLiquor) {
      setError('Brand and Base Liquor are required to suggest a subtype.')
      return
    }

    const result = suggestLiquorSubtypeOptions(brand, baseLiquor)
    if (!result.options.length) {
      setError('No subtype suggestion found for this brand/base liquor yet.')
      return
    }

    setAlcoholTypeSuggestions(result.options)
    setAlcoholTypeSuggestionFamily(result.family)
    if (result.options.length === 1) {
      updateAlcoholFormField('Type', result.options[0])
    }
    setError('')
  }

  const fetchAlcoholImageCandidates = async () => {
    const brand = String(alcoholForm.Brand || '').trim()
    const alcoholType = String(alcoholForm.Type || '').trim()
    if (!brand) {
      setError('Brand is required before fetching image candidates.')
      return
    }

    setAlcoholImageFetchLoading(true)
    try {
      const params = new URLSearchParams({ brand })
      if (alcoholType) {
        params.set('type', alcoholType)
      }

      const res = await fetch(`${API_BASE}/alcohol-image-candidates?${params.toString()}`)
      const payload = await res.json()
      if (!res.ok) {
        throw new Error(payload?.detail || 'Failed to fetch alcohol image candidates')
      }

      setAlcoholImageCandidates(Array.isArray(payload?.items) ? payload.items : [])
      setError('')
    } catch (e) {
      setError(e.message || 'Failed to fetch alcohol image candidates')
      setAlcoholImageCandidates([])
    } finally {
      setAlcoholImageFetchLoading(false)
    }
  }

  const saveAlcoholImageCandidate = async (candidate) => {
    const brand = String(alcoholForm.Brand || '').trim()
    if (!brand) {
      setError('Brand is required before selecting an image.')
      return
    }

    const imageUrl = String(candidate?.image_url || '').trim()
    if (!imageUrl) {
      setError('Selected candidate has no image URL.')
      return
    }

    setAlcoholImageSaveLoadingUrl(imageUrl)
    try {
      const res = await fetch(`${API_BASE}/alcohol-image-save-from-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand,
          type: String(alcoholForm.Type || '').trim(),
          image_url: imageUrl
        })
      })

      const payload = await res.json()
      if (!res.ok) {
        throw new Error(payload?.detail || 'Failed to save selected image')
      }

      updateAlcoholFormField('image_path', String(payload?.image_path || '').trim())
      setAlcoholImageCandidates([])
      setError('')
    } catch (e) {
      setError(e.message || 'Failed to save selected image')
    } finally {
      setAlcoholImageSaveLoadingUrl('')
    }
  }

  const resetAlcoholForm = () => {
    setSelectedAlcohol(null)
    setAlcoholForm(EMPTY_ALCOHOL_FORM)
    setAlcoholEditorMode('view')
    setAlcoholImageCandidates([])
    setAlcoholTypeSuggestions([])
    setAlcoholTypeSuggestionFamily('')
  }

  const startCreateAlcohol = () => {
    if (!ensureEditAccess()) return

    setSelectedAlcohol(null)
    setAlcoholForm({ ...EMPTY_ALCOHOL_FORM, image_path: 'images/liquors/' })
    setAlcoholEditorMode('create')
    setAlcoholImageCandidates([])
    setAlcoholTypeSuggestions([])
    setAlcoholTypeSuggestionFamily('')
  }

  const startEditAlcohol = () => {
    if (!ensureEditAccess()) return

    if (!selectedAlcohol?._rowid) {
      setError('Select an alcohol row before updating')
      return
    }
    setAlcoholForm(mapAlcoholRowToForm(selectedAlcohol))
    setAlcoholEditorMode('edit')
    setAlcoholImageCandidates([])
    setAlcoholTypeSuggestions([])
    setAlcoholTypeSuggestionFamily('')
    setError('')
  }

  const cancelAlcoholEdit = () => {
    if (selectedAlcohol?._rowid) {
      setAlcoholForm(mapAlcoholRowToForm(selectedAlcohol))
    } else {
      setAlcoholForm(EMPTY_ALCOHOL_FORM)
    }
    setAlcoholEditorMode('view')
    setAlcoholImageCandidates([])
    setAlcoholTypeSuggestions([])
    setAlcoholTypeSuggestionFamily('')
  }

  const saveAlcoholForm = async () => {
    if (!ensureEditAccess()) return

    if (!alcoholForm.Brand.trim()) {
      setError('Brand is required for alcohol records')
      return
    }

    try {
      const payload = {
        ...alcoholForm,
        ABV: normalizeAbvValue(alcoholForm.ABV),
        Price_NZD_700ml: normalizePriceValue(alcoholForm.Price_NZD_700ml)
      }
      setAlcoholForm(payload)

      const hasRowId = Boolean(selectedAlcohol?._rowid)
      const url = hasRowId
        ? `${API_BASE}/alcohol/id/${selectedAlcohol._rowid}`
        : `${API_BASE}/alcohol`
      const method = hasRowId ? 'PUT' : 'POST'

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        throw new Error(hasRowId ? 'Failed to update alcohol record' : 'Failed to create alcohol record')
      }

      const data = await res.json()
      const item = data.item

      setAlcohol((prev) => {
        if (hasRowId) {
          return prev.map((row) => (row._rowid === item._rowid ? item : row))
        }
        return [item, ...prev]
      })

      setCounts((prev) => {
        const current = prev || { alcohol_inventory: 0, cocktail_notes: cocktails.length }
        return {
          ...current,
          alcohol_inventory: hasRowId ? current.alcohol_inventory : current.alcohol_inventory + 1
        }
      })

      setSelectedAlcohol(item)
      setAlcoholForm(mapAlcoholRowToForm(item))
      setAlcoholEditorMode('view')
      await loadStorageSettings(true)
      setError('')
      showSuccess(hasRowId ? 'Alcohol updated' : 'Alcohol created')
    } catch (e) {
      setError(e.message || 'Failed to save alcohol record')
    }
  }

  const deleteSelectedAlcohol = async () => {
    if (!ensureEditAccess()) return

    const rowId = selectedAlcohol?._rowid
    if (!rowId) return

    const alcoholName = selectedAlcohol?.Brand || 'this alcohol record'
    openConfirm(
      'Delete Alcohol Record',
      `This will permanently delete "${alcoholName}". Continue?`,
      async () => {
        if (!ensureEditAccess()) return

        try {
          const res = await fetch(`${API_BASE}/alcohol/id/${rowId}`, { method: 'DELETE' })
          if (!res.ok) {
            throw new Error('Failed to delete alcohol record')
          }

          setAlcohol((prev) => prev.filter((row) => row._rowid !== rowId))
          setCounts((prev) => {
            const current = prev || { alcohol_inventory: 0, cocktail_notes: cocktails.length }
            return {
              ...current,
              alcohol_inventory: Math.max(0, current.alcohol_inventory - 1)
            }
          })
          resetAlcoholForm()
          await loadStorageSettings(true)
          setError('')
          showSuccess('Alcohol deleted')
        } catch (e) {
          setError(e.message || 'Failed to delete alcohol record')
        }
      }
    )
  }

  const uploadEditorImage = async ({ file, category, labelValue, labelName, updateField }) => {
    const trimmedLabel = String(labelValue || '').trim()
    if (!trimmedLabel) {
      setError(`${labelName} is required before adding an image.`)
      return
    }

    if (!file || !String(file.type || '').startsWith('image/')) {
      setError('Please use a valid image file.')
      return
    }

    const slug = slugifyFileLabel(trimmedLabel)
    if (!slug) {
      setError(`${labelName} must include letters or numbers before adding an image.`)
      return
    }

    try {
      const compressedFile = await compressImageToUploadJpeg(file)
      const filename = `${slug}-${formatFileTimestamp()}.jpg`
      const dataUrl = await fileToDataUrl(compressedFile)

      const res = await fetch(`${API_BASE}/image-upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category,
          filename,
          data_base64: dataUrl
        })
      })

      let payload = null
      try {
        payload = await res.json()
      } catch {
        payload = null
      }

      if (!res.ok) {
        throw new Error(payload?.detail || 'Failed to upload image')
      }

      const nextPath = String(payload?.image_path || '').trim()
      if (!nextPath) {
        throw new Error('Image upload response missing image path')
      }

      updateField('image_path', nextPath)
      setError('')
    } catch (e) {
      setError(e.message || 'Failed to upload image')
    }
  }

  const handleAlcoholImageDrop = async (event) => {
    event.preventDefault()
    if (alcoholEditorMode === 'view') return

    const file = event.dataTransfer?.files?.[0]
    if (!file) return

    await uploadEditorImage({
      file,
      category: 'liquors',
      labelValue: alcoholForm.Brand,
      labelName: 'Brand',
      updateField: updateAlcoholFormField
    })
  }

  const handleCocktailImageDrop = async (event) => {
    event.preventDefault()
    if (cocktailEditorMode === 'view') return

    const file = event.dataTransfer?.files?.[0]
    if (!file) return

    await uploadEditorImage({
      file,
      category: 'cocktails',
      labelValue: cocktailForm.Cocktail_Name,
      labelName: 'Cocktail Name',
      updateField: updateCocktailFormField
    })
  }

  const handleAlcoholImagePickerChange = async (event) => {
    if (alcoholEditorMode === 'view') return

    const file = event.target?.files?.[0]
    event.target.value = ''
    if (!file) return

    await uploadEditorImage({
      file,
      category: 'liquors',
      labelValue: alcoholForm.Brand,
      labelName: 'Brand',
      updateField: updateAlcoholFormField
    })
  }

  const handleCocktailImagePickerChange = async (event) => {
    if (cocktailEditorMode === 'view') return

    const file = event.target?.files?.[0]
    event.target.value = ''
    if (!file) return

    await uploadEditorImage({
      file,
      category: 'cocktails',
      labelValue: cocktailForm.Cocktail_Name,
      labelName: 'Cocktail Name',
      updateField: updateCocktailFormField
    })
  }

  const handleAlcoholEditorPaste = async (event) => {
    if (mainSection !== 'library' || activeTab !== 'alcohol' || alcoholEditorMode === 'view') return

    const file = clipboardImageFile(event)
    if (!file) return

    event.preventDefault()
    await uploadEditorImage({
      file,
      category: 'liquors',
      labelValue: alcoholForm.Brand,
      labelName: 'Brand',
      updateField: updateAlcoholFormField
    })
  }

  const handleCocktailEditorPaste = async (event) => {
    if (mainSection !== 'library' || activeTab !== 'cocktails' || cocktailEditorMode === 'view') return

    const file = clipboardImageFile(event)
    if (!file) return

    event.preventDefault()
    await uploadEditorImage({
      file,
      category: 'cocktails',
      labelValue: cocktailForm.Cocktail_Name,
      labelName: 'Cocktail Name',
      updateField: updateCocktailFormField
    })
  }

  const addTastingLog = async () => {
    if (!ensureEditAccess()) return

    const cocktailName = tastingForm.cocktail_name.trim()
    if (!cocktailName || !tastingForm.date) return
    if (!isValidFiveScaleValue(tastingForm.rating)) {
      setError('Tasting rating must be between 0 and 5 (decimals allowed).')
      return
    }

    const datePayload = /^\d{4}-\d{2}-\d{2}$/.test(String(tastingForm.date || '').trim())
      ? `${tastingForm.date}T${new Date().toTimeString().slice(0, 8)}`
      : tastingForm.date

    try {
      const res = await fetch(`${API_BASE}/tasting-logs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: datePayload,
          cocktail_name: cocktailName,
          rating: formatNumericString(tastingForm.rating.trim()),
          notes: tastingForm.notes.trim(),
          mood: tastingForm.mood.trim(),
          occasion: tastingForm.occasion.trim(),
          location: tastingForm.location.trim(),
          would_make_again: tastingForm.would_make_again.trim(),
          change_next_time: tastingForm.change_next_time.trim(),
          sweetness: tastingForm.sweetness,
          sourness: tastingForm.sourness,
          bitterness: tastingForm.bitterness,
          booziness: tastingForm.booziness,
          body: tastingForm.body,
          aroma: tastingForm.aroma,
          balance: tastingForm.balance,
          finish: tastingForm.finish
        })
      })

      if (!res.ok) {
        throw new Error('Failed to save tasting log')
      }

      const created = await res.json()
      setTastingLogs((prev) => {
        const next = [normalizeTastingItem(created), ...prev]
        setSelectedTastingLogId(created.id)
        return next
      })
      setTastingForm((prev) => ({
        ...buildEmptyTastingForm(),
        date: prev.date,
        cocktail_name: prev.cocktail_name
      }))

      const insightsRes = await fetch(`${API_BASE}/analytics/tasting-insights`)
      if (insightsRes.ok) {
        setTastingInsights(await insightsRes.json())
      }
      await loadStorageSettings(true)
      showSuccess('Tasting log added')
    } catch (e) {
      setError(e.message || 'Failed to save tasting log')
    }
  }

  const removeTastingLog = async (id) => {
    if (!ensureEditAccess()) return

    openConfirm(
      'Delete Tasting Entry',
      'This will permanently remove the selected tasting log. Continue?',
      async () => {
        if (!ensureEditAccess()) return

        try {
          const res = await fetch(`${API_BASE}/tasting-logs/${id}`, { method: 'DELETE' })
          if (!res.ok) {
            throw new Error('Failed to delete tasting log')
          }
          setTastingLogs((prev) => {
            const next = prev.filter((entry) => entry.id !== id)
            if (selectedTastingLogId === id) {
              setSelectedTastingLogId(next[0]?.id || '')
            }
            return next
          })

          const insightsRes = await fetch(`${API_BASE}/analytics/tasting-insights`)
          if (insightsRes.ok) {
            setTastingInsights(await insightsRes.json())
          }
          await loadStorageSettings(true)
          showSuccess('Tasting log removed')
        } catch (e) {
          setError(e.message || 'Failed to delete tasting log')
        }
      }
    )
  }

  const shiftTastingMonth = (delta) => {
    setTastingMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1))
  }

  const generateAiTwists = async () => {
    const cocktailName = aiCocktailName.trim()
    if (!cocktailName) {
      setAiNote('Please select a cocktail first.')
      return
    }

    const selected = cocktails.find((row) => row.Cocktail_Name === cocktailName)
    const ingredients = selected?.Ingredients || ''

    setAiLoading(true)
    setAiNote('')
    try {
      const res = await fetch(`${API_BASE}/ai/twist-suggestions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: aiProvider,
          cocktail_name: cocktailName,
          ingredients,
          constraints: aiConstraints,
          prompt: aiPrompt
        })
      })

      if (!res.ok) {
        throw new Error('Failed to generate suggestions')
      }

      const data = await res.json()
      setAiSuggestions(
        Array.isArray(data.suggestions)
          ? data.suggestions.map((item, index) => normalizeAiSuggestion(item, index))
          : []
      )
      setAiNote(data.note || '')
    } catch (e) {
      setAiSuggestions([])
      setAiNote(e.message || 'Could not generate twists right now.')
    } finally {
      setAiLoading(false)
    }
  }

  const renderDetail = (item, fields) => {
    if (!item) {
      return <p className="empty">Select a row to view details.</p>
    }

    return (
      <dl className="detail-list">
        {fields.map(([label, key]) => (
          <div key={key} className="detail-row">
            <dt>{label}</dt>
            <dd>{item[key] || '-'}</dd>
          </div>
        ))}
      </dl>
    )
  }

  const renderAlcoholCountryDetail = () => {
    if (!selectedAlcohol) {
      return <p className="empty">Select a row to view details.</p>
    }

    const country = String(selectedAlcohol.Country || '').trim() || '-'
    const flagUrl = alcoholCountryFlagPath ? resolveImageUrl(alcoholCountryFlagPath) : ''

    return (
      <div className="detail-row">
        <dt>Country</dt>
        <dd>
          {flagUrl ? (
            <span className="country-flag-inline">
              <img className="country-flag-inline-img" src={flagUrl} alt={`${country} flag`} />
              <span>{country}</span>
            </span>
          ) : country}
        </dd>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="hero hero-personal">
        <p className="hero-kicker">The Art of the Pour, Perfected</p>
        <h1>The Brenchley Road Curators</h1>
        <p className="hero-subtitle">of Lyttelton</p>
        <p>A private ledger for bottles, recipes, and tasting history</p>
        <p className="hero-credit">crafted by Jaime Sevilla and Jason Reimer</p>
        <p className={`edit-lock-badge ${isEditUnlocked ? 'unlocked' : 'locked'}`}>
          {isEditUnlocked ? `Edit unlocked · auto-lock in ${remainingEditUnlockMinutes}m` : 'Edit locked'}
        </p>
      </header>

      {error && <p className="error">{error}</p>}
      {successNotice && <p className="success">{successNotice}</p>}
      {backendRestarting && <p className="loading">Backend restarting... reconnecting automatically.</p>}
      {loading && <p className="loading">Loading data from API...</p>}

      {confirmDialog.open && (
        <div className="confirm-overlay" role="dialog" aria-modal="true" aria-label={confirmDialog.title || 'Confirm action'}>
          <div className="confirm-modal">
            <h3>{confirmDialog.title || 'Confirm Action'}</h3>
            <p>{confirmDialog.message || 'Are you sure you want to continue?'}</p>
            <div className="advanced-row">
              <button className="tab" onClick={closeConfirm}>Cancel</button>
              <button
                className="tab active"
                onClick={() => {
                  const action = confirmDialog.action
                  closeConfirm()
                  if (typeof action === 'function') {
                    action()
                  }
                }}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      <section className="cards">
        <article className="card card-overview">
          <h2>Library Overview</h2>
          <div className="library-kpi-grid">
            {libraryOverviewCards.map((card) => (
              <div key={card.key} className="library-kpi-tile">
                <span>{card.label}</span>
                <strong>{card.value}</strong>
              </div>
            ))}
          </div>
        </article>
        <article className="card quick-actions-card">
          <h2>Quick Actions</h2>
          <div className="quick-actions-grid">
            <button className="tab active" onClick={() => { if (!ensureEditAccess()) return; setMainSection('library'); setActiveTab('alcohol'); startCreateAlcohol() }}>{withWriteLockIcon('Add Bottle')}</button>
            <button className="tab active" onClick={() => { if (!ensureEditAccess()) return; setMainSection('library'); setActiveTab('cocktails'); startCreateCocktail() }}>{withWriteLockIcon('Add Cocktail')}</button>
            <button className="tab" onClick={() => setMainSection('tasting')}>Log Tasting</button>
            <button className="tab" onClick={() => loadApiData()} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh Data'}</button>
          </div>
        </article>
      </section>

      <section className="top-switch">
        <button
          className={mainSection === 'library' ? 'tab active' : 'tab'}
          onClick={() => setMainSection('library')}
        >
          Library
        </button>
        <button
          className={mainSection === 'tasting' ? 'tab active' : 'tab'}
          onClick={() => setMainSection('tasting')}
        >
          Tasting
        </button>
        <button
          className={mainSection === 'mixlab' ? 'tab active' : 'tab'}
          onClick={() => setMainSection('mixlab')}
        >
          Mix Lab and AI
        </button>
        <button
          className={mainSection === 'insights' ? 'tab active' : 'tab'}
          onClick={() => setMainSection('insights')}
        >
          Insights
        </button>
        <button
          className={mainSection === 'settings' ? 'tab active' : 'tab'}
          onClick={() => setMainSection('settings')}
        >
          Settings
        </button>
      </section>

      {mainSection === 'library' ? (
      <section className="workspace">
        <div className="toolbar">
          <div className="tabs">
            <button
              className={activeTab === 'alcohol' ? 'tab active' : 'tab'}
              onClick={() => setActiveTab('alcohol')}
            >
              Alcohol Inventory
            </button>
            <button
              className={activeTab === 'cocktails' ? 'tab active' : 'tab'}
              onClick={() => setActiveTab('cocktails')}
            >
              Cocktail Recipes
            </button>
          </div>
          <input
            className="search"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              activeTab === 'alcohol'
                ? 'Search brand, type, country, availability...'
                : 'Search name, base spirit, brand, ingredients...'
            }
          />
          <button className="tab" onClick={() => loadApiData()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh Data'}
          </button>
        </div>

        <div className="advanced-row">
          {activeTab === 'alcohol' ? (
            <>
              <select
                className="filter-input"
                value={alcoholBaseLiquorFilter}
                onChange={(e) => setAlcoholBaseLiquorFilter(e.target.value)}
              >
                <option value="all">All Base Liquors</option>
                {alcoholBaseLiquorOptions.map((value) => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
              <select
                className="filter-input"
                value={alcoholAvailabilityFilter}
                onChange={(e) => setAlcoholAvailabilityFilter(e.target.value)}
              >
                <option value="all">All Availability</option>
                {alcoholAvailabilityOptions.map((value) => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
            </>
          ) : (
            <>
              <select
                className="filter-input"
                value={cocktailBaseSpiritFilter}
                onChange={(e) => setCocktailBaseSpiritFilter(e.target.value)}
              >
                <option value="all">All Base Spirits</option>
                {cocktailBaseSpiritOptions.map((value) => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
              <input
                className="filter-input"
                type="number"
                step="0.1"
                min="0"
                max="5"
                placeholder="Min rating (0-5)"
                value={cocktailMinRatingFilter}
                onChange={(e) => updateCocktailMinRatingFilter(e.target.value)}
              />
              <select
                className="filter-input"
                value={cocktailMaxDifficultyFilter}
                onChange={(e) => setCocktailMaxDifficultyFilter(e.target.value)}
              >
                <option value="all">Any Difficulty</option>
                <option value="1">Difficulty 1</option>
                <option value="2">Difficulty 2</option>
                <option value="3">Difficulty 3</option>
                <option value="4">Difficulty 4</option>
                <option value="5">Difficulty 5</option>
              </select>
            </>
          )}

          <input
            className="filter-input view-name"
            type="text"
            value={viewName}
            placeholder="Saved view name"
            onChange={(e) => setViewName(e.target.value)}
          />
          <button className="tab active" onClick={saveCurrentView}>Save View</button>
        </div>

        {savedViews.length > 0 && (
          <div className="saved-views">
            {savedViews.map((view) => (
              <div key={view.id} className="saved-view-chip">
                <button className="saved-view-btn" onClick={() => applySavedView(view)}>
                  {view.name}
                </button>
                <button className="saved-view-remove" onClick={() => removeSavedView(view.id)}>
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'alcohol' ? (
          <div className="grid two-col">
            <article className="panel">
              <h3>Alcohol ({filteredAlcohol.length})</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Brand</th>
                      <th>Base Liquor</th>
                      <th>Type</th>
                      <th>Country</th>
                      <th>Availability</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAlcohol.map((row, idx) => (
                      <tr
                        key={`${row.Brand}-${row.Type}-${idx}`}
                        className={selectedAlcohol === row ? 'selected' : ''}
                        onClick={() => setSelectedAlcohol(row)}
                      >
                        <td>{row.Brand || '-'}</td>
                        <td>{row.Base_Liquor || '-'}</td>
                        <td>{row.Type || '-'}</td>
                        <td>{row.Country || '-'}</td>
                        <td>{row.Availability || '-'}</td>
                      </tr>
                    ))}
                    {filteredAlcohol.length === 0 && (
                      <tr>
                        <td colSpan={5}>No alcohol records match this filter.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </article>

            <article className="panel" onPaste={handleAlcoholEditorPaste}>
              <h3>Alcohol Editor</h3>
              <div className="advanced-row">
                <button className="tab" onClick={startEditAlcohol} disabled={!selectedAlcohol?._rowid}>
                  {withWriteLockIcon('Update')}
                </button>
                <button className="tab" onClick={startCreateAlcohol}>{withWriteLockIcon('Add New')}</button>
                <button className="tab" onClick={deleteSelectedAlcohol} disabled={!selectedAlcohol?._rowid}>
                  {withWriteLockIcon('Delete')}
                </button>
                {alcoholEditorMode !== 'view' && (
                  <button className="tab" onClick={fetchAlcoholImageCandidates} disabled={alcoholImageFetchLoading || !String(alcoholForm.Brand || '').trim()}>
                    {alcoholImageFetchLoading ? 'Fetching...' : 'Fetch Image'}
                  </button>
                )}
              </div>

              {alcoholEditorMode !== 'view' && (
                <>
                  <p className="empty">{alcoholEditorMode === 'edit' ? 'Update selected alcohol record' : 'Add a new alcohol record'}</p>
                  <div className="advanced-row">
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Brand *"
                      title="Required: Brand name of the alcohol bottle."
                      value={alcoholForm.Brand}
                      onChange={(e) => updateAlcoholFormField('Brand', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Base Liquor"
                      title="Primary liquor family (e.g., Gin, Rum, Vodka, Whiskey)."
                      value={alcoholForm.Base_Liquor}
                      onChange={(e) => updateAlcoholFormField('Base_Liquor', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Type"
                      title="Style or subtype of the liquor (e.g., London Dry, Bourbon, Blanco)."
                      value={alcoholForm.Type}
                      onChange={(e) => updateAlcoholFormField('Type', e.target.value)}
                    />
                    <button
                      className="tab"
                      type="button"
                      title="Suggest subtype from Brand and Base Liquor"
                      onClick={suggestAlcoholType}
                      disabled={!String(alcoholForm.Brand || '').trim() || !String(alcoholForm.Base_Liquor || '').trim()}
                    >
                      Suggest Type
                    </button>
                    <button
                      className="tab"
                      type="button"
                      title="Pre-fill Country, Price, ABV and Substitute from existing records"
                      onClick={prefillAlcoholDetails}
                      disabled={!String(alcoholForm.Brand || '').trim()}
                    >
                      Prefill Details
                    </button>
                    <button
                      className="tab"
                      type="button"
                      title="Lookup web hints for taste, price, ABV, and type suggestions"
                      onClick={lookupAlcoholWebHints}
                      disabled={alcoholWebLookupLoading || !String(alcoholForm.Brand || '').trim()}
                    >
                      {alcoholWebLookupLoading ? 'Looking up...' : 'Web Lookup'}
                    </button>
                    {alcoholTypeSuggestions.length > 0 && (
                      <select
                        className="filter-input"
                        title="Select a suggested style/subtype"
                        defaultValue=""
                        onChange={(e) => {
                          const selected = String(e.target.value || '').trim()
                          if (!selected) return
                          updateAlcoholFormField('Type', selected)
                          setError('')
                        }}
                      >
                        <option value="">Choose suggested {alcoholTypeSuggestionFamily ? prettyLabel(alcoholTypeSuggestionFamily) : 'type'}</option>
                        {alcoholTypeSuggestions.map((item) => (
                          <option key={item} value={item}>{item}</option>
                        ))}
                      </select>
                    )}
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="ABV"
                      title="Alcohol by volume percentage (e.g., 40%)."
                      value={alcoholForm.ABV}
                      onChange={(e) => updateAlcoholFormField('ABV', e.target.value)}
                      onBlur={() => finalizeAlcoholFormattedField('ABV')}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Country"
                      title="Country of origin for this bottle."
                      value={alcoholForm.Country}
                      onChange={(e) => updateAlcoholFormField('Country', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Price"
                      title="Bottle price (NZD, typically for 700ml)."
                      value={alcoholForm.Price_NZD_700ml}
                      onChange={(e) => updateAlcoholFormField('Price_NZD_700ml', e.target.value)}
                      onBlur={() => finalizeAlcoholFormattedField('Price_NZD_700ml')}
                    />
                    <p className="field-help">ABV auto-stores with `%` and Price auto-stores with `$`.</p>
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Availability"
                      title="Current availability status (e.g., Yes/No, In stock)."
                      value={alcoholForm.Availability}
                      onChange={(e) => updateAlcoholFormField('Availability', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Substitute"
                      title="Alternative bottle you can use if this one is unavailable."
                      value={alcoholForm.Substitute}
                      onChange={(e) => updateAlcoholFormField('Substitute', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Image Path"
                      title="Relative path to the alcohol image file."
                      value={alcoholForm.image_path}
                      onChange={(e) => updateAlcoholFormField('image_path', e.target.value)}
                    />
                    <textarea
                      className="ingredients-input"
                      rows={4}
                      placeholder="Taste"
                      title="Tasting notes or flavor profile summary for this alcohol."
                      value={alcoholForm.Taste}
                      onChange={(e) => updateAlcoholFormField('Taste', e.target.value)}
                    />
                  </div>
                  <div
                    className="image-dropzone"
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={handleAlcoholImageDrop}
                  >
                    Drop or paste image to save in <code>images/liquors</code> (Brand required). Images auto-convert to JPEG under 5MB.
                  </div>
                  <div className="advanced-row">
                    <label className="tab image-picker-btn" htmlFor="alcohol-image-picker">Take / Choose Photo</label>
                    <input
                      id="alcohol-image-picker"
                      className="image-file-input"
                      type="file"
                      accept="image/*"
                      capture="environment"
                      onChange={handleAlcoholImagePickerChange}
                    />
                  </div>
                  {alcoholImageCandidates.length > 0 && (
                    <div className="image-candidate-list">
                      {alcoholImageCandidates.map((candidate) => {
                        const candidateUrl = String(candidate.image_url || '')
                        const isSaving = alcoholImageSaveLoadingUrl === candidateUrl
                        return (
                          <div key={candidateUrl || candidate.title} className="image-candidate-item">
                            <div className="image-candidate-preview">
                              {candidate.thumbnail_url ? (
                                <img src={candidate.thumbnail_url} alt={candidate.title || 'candidate'} />
                              ) : (
                                <span>No preview</span>
                              )}
                            </div>
                            <div className="image-candidate-meta">
                              <strong>{candidate.title || 'Untitled image'}</strong>
                              <a href={candidate.source_page_url} target="_blank" rel="noreferrer">View source</a>
                            </div>
                            <button className="tab" onClick={() => saveAlcoholImageCandidate(candidate)} disabled={Boolean(alcoholImageSaveLoadingUrl)}>
                              {isSaving ? 'Saving...' : 'Use This Image'}
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  )}
                  {!alcoholImageFetchLoading && alcoholImageCandidates.length === 0 && (
                    <p className="empty">Use <strong>Fetch Image</strong> to search Wikimedia candidates by Brand + Type.</p>
                  )}
                  <div className="advanced-row">
                    <button className="tab active" onClick={saveAlcoholForm}>
                      {alcoholEditorMode === 'edit' ? withWriteLockIcon('Save Update') : withWriteLockIcon('Create')}
                    </button>
                    <button className="tab" onClick={cancelAlcoholEdit}>Cancel</button>
                  </div>
                </>
              )}

              <div className="editor-image-wrap">
                {alcoholImageUrl ? <img className="editor-image" src={alcoholImageUrl} alt="Alcohol" /> : <p className="empty">No alcohol image</p>}
              </div>

              <h3>Alcohol Details</h3>
              {selectedAlcohol ? (
                <dl className="detail-list">
                  <div className="detail-row">
                    <dt>Brand</dt>
                    <dd>{selectedAlcohol.Brand || '-'}</dd>
                  </div>
                  <div className="detail-row">
                    <dt>Base Liquor</dt>
                    <dd>{selectedAlcohol.Base_Liquor || '-'}</dd>
                  </div>
                  <div className="detail-row">
                    <dt>Type</dt>
                    <dd>{selectedAlcohol.Type || '-'}</dd>
                  </div>
                  <div className="detail-row">
                    <dt>ABV</dt>
                    <dd>{selectedAlcohol.ABV || '-'}</dd>
                  </div>
                  {renderAlcoholCountryDetail()}
                  <div className="detail-row">
                    <dt>Price</dt>
                    <dd>{selectedAlcohol.Price_NZD_700ml || '-'}</dd>
                  </div>
                  <div className="detail-row">
                    <dt>Taste</dt>
                    <dd>{selectedAlcohol.Taste || '-'}</dd>
                  </div>
                  <div className="detail-row">
                    <dt>Substitute</dt>
                    <dd>{selectedAlcohol.Substitute || '-'}</dd>
                  </div>
                  <div className="detail-row">
                    <dt>Availability</dt>
                    <dd>{selectedAlcohol.Availability || '-'}</dd>
                  </div>
                  <div className="detail-row">
                    <dt>Image Path</dt>
                    <dd>{selectedAlcohol.image_path || '-'}</dd>
                  </div>
                </dl>
              ) : (
                <p className="empty">Select a row to view details.</p>
              )}
            </article>
          </div>
        ) : (
          <div className="grid two-col">
            <article className="panel">
              <h3>Cocktails ({filteredCocktails.length})</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Base Spirit</th>
                      <th>Brand</th>
                      <th>Rating</th>
                      <th>Difficulty</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCocktails.map((row, idx) => (
                      <tr
                        key={`${row.Cocktail_Name}-${idx}`}
                        className={selectedCocktail === row ? 'selected' : ''}
                        onClick={() => setSelectedCocktail(row)}
                      >
                        <td>{row.Cocktail_Name || '-'}</td>
                        <td>{row.Base_spirit_1 || '-'}</td>
                        <td>{row.Brand1 || '-'}</td>
                        <td>{row.Rating_overall || '-'}</td>
                        <td>{row.Difficulty || '-'}</td>
                      </tr>
                    ))}
                    {filteredCocktails.length === 0 && (
                      <tr>
                        <td colSpan={5}>No cocktail records match this filter.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </article>

            <article className="panel" onPaste={handleCocktailEditorPaste}>
              <h3>Cocktail Editor</h3>
              <div className="advanced-row">
                <button className="tab" onClick={startEditCocktail} disabled={!selectedCocktail?._rowid}>
                  {withWriteLockIcon('Update')}
                </button>
                <button className="tab" onClick={startCreateCocktail}>{withWriteLockIcon('Add New')}</button>
                <button className="tab" onClick={deleteSelectedCocktail} disabled={!selectedCocktail?._rowid}>
                  {withWriteLockIcon('Delete')}
                </button>
              </div>

              {cocktailEditorMode !== 'view' && (
                <>
                  <p className="empty">{cocktailEditorMode === 'edit' ? 'Update selected cocktail record' : 'Add a new cocktail record'}</p>
                  <div className="advanced-row">
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Cocktail Name *"
                      title="Required: Name of the cocktail recipe."
                      value={cocktailForm.Cocktail_Name}
                      onChange={(e) => updateCocktailFormField('Cocktail_Name', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Base Spirit 1"
                      title="Primary base spirit used in the cocktail (e.g., Gin, Rum, Tequila)."
                      value={cocktailForm.Base_spirit_1}
                      onChange={(e) => updateCocktailFormField('Base_spirit_1', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Type 1"
                      title="Style/category of Base Spirit 1 (e.g., London Dry, Blanco, Añejo)."
                      value={cocktailForm.Type1}
                      onChange={(e) => updateCocktailFormField('Type1', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Brand 1"
                      title="Specific bottle brand for Base Spirit 1 used in this recipe."
                      value={cocktailForm.Brand1}
                      onChange={(e) => updateCocktailFormField('Brand1', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Base Spirit 2"
                      title="Secondary base spirit, if the cocktail uses two spirit bases."
                      value={cocktailForm.Base_spirit_2}
                      onChange={(e) => updateCocktailFormField('Base_spirit_2', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Type 2"
                      title="Style/category of Base Spirit 2."
                      value={cocktailForm.Type2}
                      onChange={(e) => updateCocktailFormField('Type2', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Brand 2"
                      title="Specific bottle brand for Base Spirit 2."
                      value={cocktailForm.Brand2}
                      onChange={(e) => updateCocktailFormField('Brand2', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Overall Rating"
                      title="Overall cocktail rating (use decimal values if needed)."
                      value={cocktailForm.Rating_overall}
                      onChange={(e) => updateCocktailFormField('Rating_overall', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Difficulty"
                      title="Preparation difficulty level (commonly 1 to 5)."
                      value={cocktailForm.Difficulty}
                      onChange={(e) => updateCocktailFormField('Difficulty', e.target.value)}
                    />
                    <p className="field-help">Rating and difficulty must be `0-5` (decimals allowed).</p>
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Prep Time"
                      title="Estimated time to prepare the drink (e.g., 5 min)."
                      value={cocktailForm.Prep_Time}
                      onChange={(e) => updateCocktailFormField('Prep_Time', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Citrus"
                      title="Citrus component used (e.g., lemon juice, lime wedge, orange peel)."
                      value={cocktailForm.Citrus}
                      onChange={(e) => updateCocktailFormField('Citrus', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Garnish"
                      title="Final garnish used for presentation or aroma."
                      value={cocktailForm.Garnish}
                      onChange={(e) => updateCocktailFormField('Garnish', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Date Added"
                      title="Date/time this cocktail entry was added (auto or manual)."
                      value={cocktailForm.DatetimeAdded}
                      onChange={(e) => updateCocktailFormField('DatetimeAdded', e.target.value)}
                    />
                    <input
                      className="filter-input"
                      type="text"
                      placeholder="Image Path"
                      title="Relative path to the cocktail image file."
                      value={cocktailForm.image_path}
                      onChange={(e) => updateCocktailFormField('image_path', e.target.value)}
                    />
                    <textarea
                      className="ingredients-input"
                      rows={5}
                      placeholder="Ingredients"
                      title="Ingredient list and quantities for the cocktail recipe."
                      value={cocktailForm.Ingredients}
                      onChange={(e) => updateCocktailFormField('Ingredients', e.target.value)}
                    />
                    <textarea
                      className="ingredients-input"
                      rows={4}
                      placeholder="Notes"
                      title="Extra preparation notes, tips, substitutions, or tasting comments."
                      value={cocktailForm.Notes}
                      onChange={(e) => updateCocktailFormField('Notes', e.target.value)}
                    />
                  </div>
                  <div
                    className="image-dropzone"
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={handleCocktailImageDrop}
                  >
                    Drop or paste image to save in <code>images/cocktails</code> (Cocktail Name required). Images auto-convert to JPEG under 5MB.
                  </div>
                  <div className="advanced-row">
                    <label className="tab image-picker-btn" htmlFor="cocktail-image-picker">Take / Choose Photo</label>
                    <input
                      id="cocktail-image-picker"
                      className="image-file-input"
                      type="file"
                      accept="image/*"
                      capture="environment"
                      onChange={handleCocktailImagePickerChange}
                    />
                  </div>
                  <div className="advanced-row">
                    <button className="tab active" onClick={saveCocktailForm}>
                      {cocktailEditorMode === 'edit' ? withWriteLockIcon('Save Update') : withWriteLockIcon('Create')}
                    </button>
                    <button className="tab" onClick={cancelCocktailEdit}>Cancel</button>
                  </div>
                </>
              )}

              <div className="editor-image-wrap">
                {cocktailImageUrl ? <img className="editor-image" src={cocktailImageUrl} alt="Cocktail" /> : <p className="empty">No cocktail image</p>}
              </div>

              <h3>Cocktail Details</h3>
              {renderDetail(selectedCocktail, [
                ['Name', 'Cocktail_Name'],
                ['Ingredients', 'Ingredients'],
                ['Rating (Jason)', 'Rating_Jason'],
                ['Rating (Jaime)', 'Rating_Jaime'],
                ['Rating (Overall)', 'Rating_overall'],
                ['Base Spirit 1', 'Base_spirit_1'],
                ['Type 1', 'Type1'],
                ['Brand 1', 'Brand1'],
                ['Base Spirit 2', 'Base_spirit_2'],
                ['Type 2', 'Type2'],
                ['Brand 2', 'Brand2'],
                ['Citrus', 'Citrus'],
                ['Garnish', 'Garnish'],
                ['Prep Time', 'Prep_Time'],
                ['Difficulty', 'Difficulty'],
                ['Notes', 'Notes'],
                ['Date Added', 'DatetimeAdded'],
                ['Image Path', 'image_path']
              ])}
            </article>
          </div>
        )}
      </section>
      ) : mainSection === 'tasting' ? (
      <section className="workspace">
        <div className="toolbar">
          <div className="tabs">
            <button className="tab" onClick={() => shiftTastingMonth(-1)}>◀</button>
            <button className="tab active">{tastingMonthLabel}</button>
            <button className="tab" onClick={() => shiftTastingMonth(1)}>▶</button>
          </div>
          <button className="tab" onClick={() => loadApiData()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh Data'}
          </button>
        </div>

        <div className="grid two-col">
          <article className="panel">
            <h3>Add Tasting Entry</h3>
            <div className="advanced-row">
              <input
                className="filter-input"
                type="date"
                value={tastingForm.date}
                onChange={(e) => setTastingForm((prev) => ({ ...prev, date: e.target.value }))}
              />
              <select
                className="filter-input"
                value={tastingForm.cocktail_name}
                onChange={(e) => setTastingForm((prev) => ({ ...prev, cocktail_name: e.target.value }))}
              >
                <option value="">Select cocktail</option>
                {cocktails.map((row) => (
                  <option key={row.Cocktail_Name} value={row.Cocktail_Name}>{row.Cocktail_Name}</option>
                ))}
              </select>
              <input
                className="filter-input"
                type="number"
                step="0.1"
                min="0"
                max="5"
                placeholder="Rating (0-5)"
                value={tastingForm.rating}
                onChange={(e) => updateTastingRatingField(e.target.value)}
              />
              <p className="field-help">Tasting rating is stored as `0-5` (decimals allowed).</p>
              <select
                className="filter-input"
                value={tastingForm.would_make_again}
                onChange={(e) => setTastingForm((prev) => ({ ...prev, would_make_again: e.target.value }))}
              >
                <option value="">Make again?</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>

            <div className="advanced-row">
              <select
                className="filter-input"
                value={tastingForm.mood}
                onChange={(e) => setTastingForm((prev) => ({ ...prev, mood: e.target.value }))}
              >
                <option value="">Mood</option>
                <option value="Relaxed">Relaxed</option>
                <option value="Celebratory">Celebratory</option>
                <option value="Experimental">Experimental</option>
                <option value="Social">Social</option>
                <option value="After-work">After-work</option>
              </select>
              <input
                className="filter-input"
                type="text"
                placeholder="Occasion"
                value={tastingForm.occasion}
                onChange={(e) => setTastingForm((prev) => ({ ...prev, occasion: e.target.value }))}
              />
              <input
                className="filter-input"
                type="text"
                placeholder="Location"
                value={tastingForm.location}
                onChange={(e) => setTastingForm((prev) => ({ ...prev, location: e.target.value }))}
              />
              <input
                className="filter-input view-name"
                type="text"
                placeholder="Notes (optional)"
                value={tastingForm.notes}
                onChange={(e) => setTastingForm((prev) => ({ ...prev, notes: e.target.value }))}
              />
            </div>

            <div className="advanced-row">
              <input
                className="filter-input view-name"
                type="text"
                placeholder="What would you change next time?"
                value={tastingForm.change_next_time}
                onChange={(e) => setTastingForm((prev) => ({ ...prev, change_next_time: e.target.value }))}
              />
              <button className="tab active" onClick={addTastingLog}>{withWriteLockIcon('Add Entry')}</button>
            </div>

            <div className="tasting-slider-grid">
              {TASTING_DIMENSIONS.map((dimension) => (
                <label key={`slider-${dimension.key}`} className="tasting-slider-item">
                  <span>{dimension.label}</span>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="1"
                    value={tastingForm[dimension.key] || 3}
                    onChange={(e) => setTastingForm((prev) => ({ ...prev, [dimension.key]: e.target.value }))}
                  />
                  <strong>{tastingForm[dimension.key] || '-'}</strong>
                </label>
              ))}
            </div>

            <div className="analytics-grid tasting-visual-grid">
              <article className="panel chart-panel">
                <h3>Rating Trend</h3>
                <div className="chart-wrap">
                  {ratingTrendChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={ratingTrendChartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5d6bf" />
                        <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                        <YAxis domain={[0, 5]} tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Line type="monotone" dataKey="avg" stroke="#7a4f24" strokeWidth={3} dot={{ r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="empty">No tasting ratings yet.</p>
                  )}
                </div>
              </article>

              <article className="panel chart-panel">
                <h3>Make Again Split</h3>
                <div className="chart-wrap">
                  {makeAgainChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={makeAgainChartData} dataKey="value" nameKey="name" outerRadius={86} innerRadius={46}>
                          {makeAgainChartData.map((entry, index) => (
                            <Cell key={`make-again-${entry.name}`} fill={index === 0 ? '#a86f35' : '#ead8bc'} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="empty">No make-again data yet.</p>
                  )}
                </div>
                <p className="empty chart-caption">Would make again: {wouldMakeAgainDisplay}</p>
              </article>
            </div>

            <h3>Tasting Entries ({tastingLogsSorted.length})</h3>
            <div className="table-wrap tasting-table">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Cocktail</th>
                    <th>Rating</th>
                    <th>Mood</th>
                    <th>Make Again</th>
                    <th>Notes</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {tastingLogsSorted.map((entry) => (
                    <tr
                      key={entry.id}
                      className={selectedTastingLog?.id === entry.id ? 'selected' : ''}
                      onClick={() => setSelectedTastingLogId(entry.id)}
                    >
                      <td>{formatDateTime(entry.date)}</td>
                      <td>{entry.cocktailName}</td>
                      <td>{entry.rating || '-'}</td>
                      <td>{entry.mood || '-'}</td>
                      <td>{entry.wouldMakeAgain || '-'}</td>
                      <td>{entry.notes || '-'}</td>
                      <td>
                        <button className="saved-view-remove" onClick={() => removeTastingLog(entry.id)}>{isEditUnlocked ? '×' : '🔒 ×'}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          <article className="panel">
            <h3>Tasting Entry Details</h3>
            {selectedTastingLog ? (
              selectedTastingDetailRows.length > 0 || selectedTastingRatingStars || selectedTastingFlavorRows.length > 0 ? (
                <>
                  <dl className="detail-list">
                    {selectedTastingDetailRows.map((row) => (
                      <div key={row.label} className="detail-row">
                        <dt>{row.label}</dt>
                        <dd>{row.value}</dd>
                      </div>
                    ))}
                    {selectedTastingRatingStars && (
                      <div className="detail-row">
                        <dt>Rating</dt>
                        <dd>
                          <div className="tasting-detail-stars">
                            <span className="tasting-detail-stars-glyph" aria-hidden="true">
                              <span className="tasting-detail-stars-base">★★★★★</span>
                              <span
                                className="tasting-detail-stars-fill"
                                style={{ width: `${selectedTastingRatingStars.fillPercent}%` }}
                              >
                                ★★★★★
                              </span>
                            </span>
                            <span className="tasting-detail-stars-value">{selectedTastingRatingStars.roundedScore.toFixed(1)}</span>
                            <span className="tasting-detail-stars-score">{selectedTastingRatingStars.score}</span>
                          </div>
                        </dd>
                      </div>
                    )}
                  </dl>
                  {selectedTastingFlavorRows.length > 0 && (
                    <div className="tasting-detail-flavor-wrap">
                      <h4 className="tasting-detail-subtitle">Flavor Profile</h4>
                      <div className="bar-list">
                        {selectedTastingFlavorRows.map((item) => (
                          <div key={item.key} className="bar-row">
                            <div className="tasting-detail-flavor-label">
                              <span className="bar-label">{item.label}</span>
                              <strong>{item.value}</strong>
                            </div>
                            <div className="bar-track">
                              <div className="bar-fill" style={{ width: `${item.percent}%` }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <p className="empty">No tasting details with values for this entry.</p>
              )
            ) : (
              <p className="empty">Select a tasting entry to view full details.</p>
            )}

            <h3>Month Summary</h3>
            <p className="empty">Entries: {tastingMonthSummary.count} • Avg Rating: {tastingMonthSummary.avgRating}</p>
            <div className="calendar-grid">
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((name) => (
                <div key={name} className="calendar-head">{name}</div>
              ))}
              {tastingCalendarDays.map((cell) => (
                <div key={cell.key} className={cell.empty ? 'calendar-cell empty-cell' : 'calendar-cell'}>
                  {!cell.empty && (
                    <>
                      <span>{cell.day}</span>
                      {cell.count > 0 && <span className="calendar-count">{cell.count}</span>}
                    </>
                  )}
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>
      ) : mainSection === 'mixlab' ? (
      <section className="workspace">
        <div className="toolbar">
          <div className="tabs">
            <button className="tab active">Mix Lab and AI</button>
          </div>
          <button className="tab" onClick={() => loadApiData()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh Data'}
          </button>
        </div>

        <div className="grid two-col">
          <article className="panel">
            <h3>What Can I Make Now?</h3>
            <p className="empty">Enter ingredients you currently have (comma or new line separated).</p>
            <textarea
              className="ingredients-input"
              rows={6}
              placeholder="e.g. gin, vermouth, lemon juice, simple syrup"
              value={availableIngredientsInput}
              onChange={(e) => setAvailableIngredientsInput(e.target.value)}
            />

            <div className="advanced-row">
              <label className="empty" htmlFor="min-score">Minimum score:</label>
              <input
                id="min-score"
                className="filter-input"
                type="number"
                min="0"
                max="100"
                value={minRecommendationScore}
                onChange={(e) => setMinRecommendationScore(Number(e.target.value || 0))}
              />
            </div>
          </article>

          <article className="panel">
            <h3>Top Matches ({recommendationResults.length})</h3>
            <div className="table-wrap tasting-table">
              <table>
                <thead>
                  <tr>
                    <th>Cocktail</th>
                    <th>Score</th>
                    <th>Coverage</th>
                    <th>Base Spirit</th>
                    <th>Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {recommendationResults.map((row) => (
                    <tr key={row.cocktailName}>
                      <td>{row.cocktailName}</td>
                      <td>{row.score}</td>
                      <td>{row.matchedCount}/{row.totalCount}</td>
                      <td>{row.baseSpirit}{row.hasBaseSpirit ? ' ✓' : ''}</td>
                      <td>{row.rating}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
        </div>

        <article className="panel">
          <h3>Missing Ingredient Hints</h3>
          <div className="saved-views">
            {recommendationResults.slice(0, 8).map((row) => (
              <div key={`hint-${row.cocktailName}`} className="recommendation-hint">
                <strong>{row.cocktailName}</strong>
                <span>
                  {row.missingIngredients.length
                    ? `Need: ${row.missingIngredients.slice(0, 4).join(', ')}`
                    : 'You have all parsed ingredients'}
                </span>
              </div>
            ))}
          </div>
        </article>

        <div className="grid two-col mixlab-ai-grid">
          <article className="panel">
            <h3>Refine with AI Twist</h3>
            <p className="empty">Choose a cocktail, set your constraints, and generate tailored twists.</p>
            <div className="advanced-row">
              <select
                className="filter-input"
                value={aiProvider}
                onChange={(e) => setAiProvider(e.target.value)}
              >
                <option value="local">Local Fallback Engine</option>
                <option value="groq">Groq Mode (requires key)</option>
                <option value="gemini">Gemini Mode (requires key)</option>
              </select>
              <select
                className="filter-input"
                value={aiCocktailName}
                onChange={(e) => setAiCocktailName(e.target.value)}
              >
                <option value="">Select cocktail</option>
                {cocktails.map((row) => (
                  <option key={`ai-${row.Cocktail_Name}`} value={row.Cocktail_Name}>{row.Cocktail_Name}</option>
                ))}
              </select>
            </div>

            <div className="advanced-row">
              <input
                className="filter-input view-name"
                type="text"
                value={aiConstraints}
                onChange={(e) => setAiConstraints(e.target.value)}
                placeholder="Constraints (e.g. low sugar, no egg white)"
              />
            </div>

            <div className="advanced-row">
              <input
                className="filter-input view-name"
                type="text"
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="Flavor direction (e.g. brighter, spicier, smoky)"
              />
              <button className="tab active" onClick={generateAiTwists}>
                {aiLoading ? 'Generating…' : 'Generate Twists'}
              </button>
            </div>

            {aiNote && <p className="loading">{aiNote}</p>}
          </article>

          <article className="panel">
            <h3>Suggested Twists ({aiSuggestions.length})</h3>
            <div className="saved-views">
              {aiSuggestions.map((suggestion, index) => (
                <div key={`ai-suggestion-${index}`} className="recommendation-hint">
                  <strong>{suggestion.name || `Twist ${index + 1}`}</strong>
                  {suggestion.flavor_goal && <span><strong>Flavor Goal:</strong> {suggestion.flavor_goal}</span>}
                  {suggestion.substitutions.length > 0 && (
                    <div className="ai-block">
                      <strong>Substitutions</strong>
                      <ul>
                        {suggestion.substitutions.map((line, lineIndex) => (
                          <li key={`ai-sub-${index}-${lineIndex}`}>{line}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {suggestion.method.length > 0 && (
                    <div className="ai-block">
                      <strong>Method</strong>
                      <ol>
                        {suggestion.method.map((line, lineIndex) => (
                          <li key={`ai-method-${index}-${lineIndex}`}>{line}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                  {suggestion.garnish_and_glass && <span><strong>Garnish & Glass:</strong> {suggestion.garnish_and_glass}</span>}
                  {suggestion.why_it_works && <span><strong>Why it works:</strong> {suggestion.why_it_works}</span>}
                  {suggestion.difficulty && <span><strong>Difficulty:</strong> {suggestion.difficulty}</span>}
                  {suggestion.risk_note && <span><strong>Risk note:</strong> {suggestion.risk_note}</span>}
                  {suggestion.wild_card && <span><strong>Wild card:</strong> {suggestion.wild_card}</span>}
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>
      ) : mainSection === 'insights' ? (
      <section className="workspace">
        <div className="toolbar">
          <div className="tabs">
            <button className="tab active">Analytics Dashboard</button>
          </div>
          <button className="tab" onClick={() => loadApiData()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh Data'}
          </button>
        </div>

        <div className="analytics-grid">
          <article className="panel chart-panel">
            <h3>Base Spirit Usage</h3>
            <div className="chart-wrap">
              {spiritUsage.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={spiritUsage} layout="vertical" margin={{ left: 8, right: 12, top: 6, bottom: 6 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5d6bf" />
                    <XAxis type="number" tick={{ fontSize: 12 }} />
                    <YAxis type="category" width={92} dataKey="name" tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#7a4f24" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="empty">No spirit usage data yet.</p>
              )}
            </div>
          </article>

          <article className="panel chart-panel">
            <h3>Difficulty Mix</h3>
            <div className="chart-wrap">
              {difficultyMixChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={difficultyMixChartData} dataKey="value" nameKey="name" outerRadius={84} innerRadius={40}>
                      {difficultyMixChartData.map((entry, index) => (
                        <Cell key={`difficulty-${entry.name}`} fill={CHART_SWATCH[index % CHART_SWATCH.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="empty">No difficulty data yet.</p>
              )}
            </div>
          </article>

          <article className="panel chart-panel">
            <h3>Tasting Trend</h3>
            <div className="chart-wrap">
              {ratingTrendChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={ratingTrendChartData}>
                    <defs>
                      <linearGradient id="ratingArea" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#b9873c" stopOpacity={0.5} />
                        <stop offset="95%" stopColor="#b9873c" stopOpacity={0.08} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5d6bf" />
                    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                    <YAxis domain={[0, 5]} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Area type="monotone" dataKey="avg" stroke="#7a4f24" fill="url(#ratingArea)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <p className="empty">No tasting ratings yet.</p>
              )}
            </div>
          </article>

          <article className="panel chart-panel">
            <h3>Flavor Profile</h3>
            <div className="chart-wrap">
              {flavorProfileChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={flavorProfileChartData}>
                    <PolarGrid stroke="#e5d6bf" />
                    <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 11 }} />
                    <PolarRadiusAxis domain={[0, 5]} tick={{ fontSize: 10 }} />
                    <Radar dataKey="avg" stroke="#7a4f24" fill="#b9873c" fillOpacity={0.35} />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <p className="empty">No flavor profile data yet.</p>
              )}
            </div>
          </article>

          <article className="panel">
            <h3>Overview KPIs</h3>
            <div className="kpi-grid">
              <div className="kpi-card">
                <span>Total Alcohol</span>
                <strong>{analyticsSummary.totalAlcohol}</strong>
              </div>
              <div className="kpi-card">
                <span>Available Alcohol</span>
                <strong>{analyticsSummary.availableAlcoholCount}</strong>
              </div>
              <div className="kpi-card">
                <span>Total Cocktails</span>
                <strong>{analyticsSummary.totalCocktails}</strong>
              </div>
              <div className="kpi-card">
                <span>Avg Cocktail Rating</span>
                <strong>{analyticsSummary.avgCocktailRating}</strong>
              </div>
              <div className="kpi-card">
                <span>Tasting Entries</span>
                <strong>{analyticsSummary.tastingCount}</strong>
              </div>
              <div className="kpi-card">
                <span>Avg Tasting Rating</span>
                <strong>{tastingInsights.avg_rating ?? '-'}</strong>
              </div>
              <div className="kpi-card">
                <span>Would Make Again %</span>
                <strong>{wouldMakeAgainDisplay}</strong>
              </div>
            </div>
          </article>

          <div className="analytics-section-tag">Performance</div>

          <article className="panel">
            <h3>Base Spirit Usage</h3>
            <div className="bar-list">
              {spiritUsage.map((row) => (
                <div key={`spirit-${row.name}`} className="bar-row">
                  <div className="bar-label">{row.name} ({row.count})</div>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${row.pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="panel">
            <h3>Difficulty Mix</h3>
            <div className="saved-views">
              <div className="recommendation-hint"><strong>Easy (1-2)</strong><span>{analyticsSummary.difficultyBuckets['1-2']}</span></div>
              <div className="recommendation-hint"><strong>Medium (3)</strong><span>{analyticsSummary.difficultyBuckets['3']}</span></div>
              <div className="recommendation-hint"><strong>Advanced (4-5)</strong><span>{analyticsSummary.difficultyBuckets['4-5']}</span></div>
            </div>
          </article>

          <article className="panel">
            <h3>Tasting Trend (Last 6 Months)</h3>
            <div className="table-wrap tasting-table">
              <table>
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Average Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {ratingTrend.length ? ratingTrend.map((row) => (
                    <tr key={`trend-${row.month}`}>
                      <td>{row.month}</td>
                      <td>{row.avg}</td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan={2}>No tasting ratings yet.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>

          <div className="analytics-section-tag">Preferences</div>

          <article className="panel">
            <h3>Flavor Profile (Avg 1-5)</h3>
            <div className="bar-list">
              {(tastingInsights.flavor_profile_avg || []).map((row) => (
                <div key={`flavor-${row.dimension}`} className="bar-row">
                  <div className="bar-label">{prettyLabel(row.dimension)} ({row.avg ?? '-'})</div>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${Math.max(0, Math.min(100, Number(row.avg || 0) * 20))}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="panel">
            <h3>Most Logged Cocktails</h3>
            <div className="chart-wrap compact-chart-wrap">
              {topCocktailsChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topCocktailsChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5d6bf" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-12} textAnchor="end" height={48} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="entries" fill="#a86f35" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : null}
            </div>
            <div className="table-wrap tasting-table">
              <table>
                <thead>
                  <tr>
                    <th>Cocktail</th>
                    <th>Entries</th>
                    <th>Avg Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {(tastingInsights.top_cocktails || []).map((row) => (
                    <tr key={`top-cocktail-${row.name}`}>
                      <td>{row.name}</td>
                      <td>{row.entries}</td>
                      <td>{row.avg_rating ?? '-'}</td>
                    </tr>
                  ))}
                  {(tastingInsights.top_cocktails || []).length === 0 && (
                    <tr><td colSpan={3}>No tasting entries yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>

          <article className="panel">
            <h3>Tasting Mood Breakdown</h3>
            <div className="chart-wrap compact-chart-wrap">
              {moodBreakdownChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={moodBreakdownChartData} dataKey="value" nameKey="name" outerRadius={88}>
                      {moodBreakdownChartData.map((row, index) => (
                        <Cell key={`mood-cell-${row.name}`} fill={CHART_SWATCH[index % CHART_SWATCH.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : null}
            </div>
            <div className="saved-views">
              {(tastingInsights.mood_breakdown || []).map((row) => (
                <div key={`mood-${row.mood}`} className="recommendation-hint">
                  <strong>{row.mood}</strong>
                  <span>{row.count} entries</span>
                </div>
              ))}
              {(tastingInsights.mood_breakdown || []).length === 0 && (
                <p className="empty">No mood data logged yet.</p>
              )}
            </div>
          </article>

          <article className="panel">
            <h3>Ratings by Base Spirit</h3>
            <div className="chart-wrap compact-chart-wrap">
              {spiritRatingChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={spiritRatingChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5d6bf" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-12} textAnchor="end" height={48} />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="avg" fill="#b9873c" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : null}
            </div>
            <div className="table-wrap tasting-table">
              <table>
                <thead>
                  <tr>
                    <th>Base Spirit</th>
                    <th>Entries</th>
                    <th>Avg Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {(tastingInsights.rating_by_base_spirit || []).map((row) => (
                    <tr key={`spirit-rating-${row.base_spirit}`}>
                      <td>{row.base_spirit}</td>
                      <td>{row.entries}</td>
                      <td>{row.avg_rating ?? '-'}</td>
                    </tr>
                  ))}
                  {(tastingInsights.rating_by_base_spirit || []).length === 0 && (
                    <tr><td colSpan={3}>No tasting/base spirit data yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>

          <div className="analytics-section-tag">Cost</div>

          <article className="panel">
            <h3>Cost & Value Snapshot</h3>
            <div className="kpi-grid">
              <div className="kpi-card">
                <span>Avg Bottle Price (NZD)</span>
                <strong>{costInsights.avg_bottle_price_nzd ?? '-'}</strong>
              </div>
              <div className="kpi-card">
                <span>Estimated Cost / Serving (NZD)</span>
                <strong>{costInsights.estimated_cost_per_serving_nzd_avg ?? '-'}</strong>
              </div>
            </div>
          </article>

          <article className="panel">
            <h3>Most Expensive Bottles</h3>
            <div className="table-wrap tasting-table">
              <table>
                <thead>
                  <tr>
                    <th>Brand</th>
                    <th>Base</th>
                    <th>Price (NZD)</th>
                  </tr>
                </thead>
                <tbody>
                  {(costInsights.top_expensive_bottles || []).map((row, idx) => (
                    <tr key={`expensive-${idx}`}>
                      <td>{row.brand}</td>
                      <td>{row.base_liquor}</td>
                      <td>{row.price_nzd}</td>
                    </tr>
                  ))}
                  {(costInsights.top_expensive_bottles || []).length === 0 && (
                    <tr><td colSpan={3}>No price data available.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>

          <article className="panel">
            <h3>Monthly Tasting Cost Estimate</h3>
            <div className="chart-wrap compact-chart-wrap">
              {monthlyCostChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={monthlyCostChartData}>
                    <defs>
                      <linearGradient id="costArea" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8f6334" stopOpacity={0.45} />
                        <stop offset="95%" stopColor="#8f6334" stopOpacity={0.08} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5d6bf" />
                    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Area type="monotone" dataKey="total" stroke="#8f6334" fill="url(#costArea)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : null}
            </div>
            <div className="table-wrap tasting-table">
              <table>
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Entries</th>
                    <th>Total Cost (NZD)</th>
                  </tr>
                </thead>
                <tbody>
                  {(costInsights.tasting_monthly_estimated_cost || []).map((row) => (
                    <tr key={`cost-${row.month}`}>
                      <td>{row.month}</td>
                      <td>{row.entries}</td>
                      <td>{row.total_estimated_cost_nzd}</td>
                    </tr>
                  ))}
                  {(costInsights.tasting_monthly_estimated_cost || []).length === 0 && (
                    <tr><td colSpan={3}>No tasting cost data yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>
        </div>
      </section>
      ) : mainSection === 'settings' ? (
      <section className="workspace">
        <div className="toolbar">
          <div className="tabs">
            <button className="tab active">Storage Settings</button>
          </div>
          <button className="tab" onClick={loadStorageSettings} disabled={storageLoading || storageApplying}>
            {storageLoading ? 'Refreshing...' : 'Refresh Settings'}
          </button>
        </div>

        {!storageSettings.backup_configured && (
          <p className="warning settings-warning">Warning: Backup location is not configured. Configure storage backup below.</p>
        )}

        <article className="panel edit-access-panel">
          <h3>Edit Access</h3>
          <p className="empty">View access is open. Editing actions require a password entered here.</p>
          <div className="advanced-row">
            <input
              className="filter-input view-name"
              type="password"
              value={editAccessPassword}
              onChange={(e) => setEditAccessPassword(e.target.value)}
              placeholder="Enter edit password"
            />
            <button className="tab active" onClick={unlockEditAccess}>Unlock</button>
            <button className="tab" onClick={() => lockEditAccess(true)} disabled={!isEditUnlocked}>Lock now</button>
          </div>
          <p className="field-help">
            {isEditUnlocked
              ? `Unlocked in this tab. Auto-lock in ${remainingEditUnlockMinutes} minute(s) without protected actions.`
              : 'Editing is currently locked. Protected write buttons will prompt for password in Settings.'}
          </p>
        </article>

        <article className="panel settings-diagnostics">
          <h3>System & Connectivity</h3>
          <div className="advanced-row">
            <span className={`api-badge ${apiHealth}`}>{apiHealth.toUpperCase()}</span>
            <span className="api-version">{APP_VERSION}</span>
            <span className="api-message">{apiHealthMessage}</span>
            <button className="tab api-retry" onClick={() => loadApiData()} disabled={loading}>
              {loading ? 'Reconnecting...' : 'Retry Connection'}
            </button>
          </div>
          <dl className="detail-list">
            <div className="detail-row">
              <dt>API Base</dt>
              <dd>{API_BASE}</dd>
            </div>
            <div className="detail-row">
              <dt>Last Refreshed</dt>
              <dd>{lastRefreshedAt ? formatDateTime(lastRefreshedAt) : '-'}</dd>
            </div>
          </dl>
        </article>

        <div className="grid two-col">
          <article className="panel">
            <h3>Current Location</h3>
            <dl className="detail-list">
              <div className="detail-row">
                <dt>Dual-save</dt>
                <dd>{storageSettings.dual_save_enabled ? 'ON (active storage mirrors to local)' : 'OFF (using local as primary)'}</dd>
              </div>
              <div className="detail-row">
                <dt>Root Folder</dt>
                <dd>{storageSettings.root_path || '-'}</dd>
              </div>
              <div className="detail-row">
                <dt>DB Source</dt>
                <dd>{storageSettings.db_source || '-'}</dd>
              </div>
              <div className="detail-row">
                <dt>Images Source</dt>
                <dd>{storageSettings.images_source || '-'}</dd>
              </div>
              <div className="detail-row">
                <dt>Database Path</dt>
                <dd>{storageSettings.db_path || '-'}</dd>
              </div>
              <div className="detail-row">
                <dt>Images Path</dt>
                <dd>{storageSettings.images_path || '-'}</dd>
              </div>
              <div className="detail-row">
                <dt>Local Mirror DB</dt>
                <dd>{storageSettings.local_db_path || '-'}</dd>
              </div>
              <div className="detail-row">
                <dt>Local Mirror Images</dt>
                <dd>{storageSettings.local_images_path || '-'}</dd>
              </div>
              <div className="detail-row">
                <dt>Last Mirror Sync</dt>
                <dd>{storageSettings.last_mirror_sync_at ? formatDateTime(storageSettings.last_mirror_sync_at) : '-'}</dd>
              </div>
              <div className="detail-row">
                <dt>Active DB Last Write</dt>
                <dd>{storageSettings.active_db_last_write_at ? formatDateTime(storageSettings.active_db_last_write_at) : '-'}</dd>
              </div>
              <div className="detail-row">
                <dt>Local DB Last Write</dt>
                <dd>{storageSettings.local_db_last_write_at ? formatDateTime(storageSettings.local_db_last_write_at) : '-'}</dd>
              </div>
            </dl>

            <h3>Change Storage Root</h3>
            <div className="advanced-row">
              <input
                className="filter-input view-name"
                type="text"
                value={storageRootInput}
                onChange={(e) => setStorageRootInput(e.target.value)}
                placeholder="Select root folder"
              />
              <button className="tab" onClick={browseStorageFolder} disabled={storageLoading || storageApplying}>
                {storageLoading ? 'Opening...' : 'Browse...'}
              </button>
              <button className="tab" onClick={() => runStoragePreflight()} disabled={storageLoading || storageApplying || !String(storageRootInput || '').trim()}>
                {storageLoading ? 'Checking...' : 'Preflight Check'}
              </button>
              <button className="tab" onClick={mirrorStorageNow} disabled={storageMirroring || storageApplying || storageLoading}>
                {storageMirroring ? 'Mirroring...' : withWriteLockIcon('Mirror Now')}
              </button>
              <button className="tab active" onClick={applyStorageSettings} disabled={storageApplying || storageLoading || !String(storageRootInput || '').trim()}>
                {storageApplying ? 'Applying...' : withWriteLockIcon('Apply')}
              </button>
            </div>
            <p className="empty">If selected folder has no <code>cocktail_database.db</code> and no <code>images</code> folder, current data is copied there. Otherwise existing and current data are merged. On restart, configured `.env` paths are loaded automatically.</p>
          </article>

          <article className="panel">
            <h3>Preflight Summary</h3>
            {storagePreflight ? (
              <dl className="detail-list">
                <div className="detail-row">
                  <dt>Action Preview</dt>
                  <dd>{storagePreflight.action_preview || '-'}</dd>
                </div>
                <div className="detail-row">
                  <dt>Empty Location</dt>
                  <dd>{storagePreflight.empty_location ? 'Yes' : 'No'}</dd>
                </div>
                <div className="detail-row">
                  <dt>Target DB</dt>
                  <dd>{storagePreflight?.target?.db_path || '-'}</dd>
                </div>
                <div className="detail-row">
                  <dt>Target Images</dt>
                  <dd>{storagePreflight?.target?.images_path || '-'}</dd>
                </div>
                <div className="detail-row">
                  <dt>Source Counts</dt>
                  <dd>{JSON.stringify(storagePreflight?.db_stats?.source?.counts || {})}</dd>
                </div>
                <div className="detail-row">
                  <dt>Target Counts</dt>
                  <dd>{JSON.stringify(storagePreflight?.db_stats?.target?.counts || {})}</dd>
                </div>
              </dl>
            ) : (
              <p className="empty">Run preflight to review copy/merge behavior before applying.</p>
            )}

            <h3>Last Apply Result</h3>
            {storageApplyReport ? (
              <dl className="detail-list">
                <div className="detail-row">
                  <dt>Status</dt>
                  <dd>{storageApplyReport.status || '-'}</dd>
                </div>
                <div className="detail-row">
                  <dt>Mode</dt>
                  <dd>{storageApplyReport?.db_report?.mode || '-'}</dd>
                </div>
                <div className="detail-row">
                  <dt>Backup Dir</dt>
                  <dd>{storageApplyReport?.backups?.backup_dir || '-'}</dd>
                </div>
                <div className="detail-row">
                  <dt>Image Copy</dt>
                  <dd>{JSON.stringify(storageApplyReport?.image_report || {})}</dd>
                </div>
              </dl>
            ) : (
              <p className="empty">No apply action yet.</p>
            )}
          </article>
        </div>
      </section>
      ) : null}
    </div>
  )
}
