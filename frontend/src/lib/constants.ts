export const API_BASE = '/api'

export const AUTH_ENDPOINTS = {
  LOGIN: '/auth/login',
  SIGNUP: '/auth/signup',
  ME: '/auth/me',
} as const

export const STORAGE_KEYS = {
  TOKEN: 'meraki_token',
} as const
