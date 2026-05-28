/**
 * Configuration Module
 * Application configuration and constants
 */

export * from './pipeline-presets';
export * from './constants';

/**
 * API Configuration
 */
export const API_CONFIG = {
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000,
} as const;

/**
 * App Configuration
 */
export const APP_CONFIG = {
  name: 'ARHIAX Dx',
  version: '5.1',
  defaultLanguage: 'es',
  supportedLanguages: ['es', 'en'],
} as const;
