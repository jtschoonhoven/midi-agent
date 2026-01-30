/**
 * Authentication utilities for managing the Anthropic API key
 */

const API_KEY_STORAGE_KEY = "anthropic_api_key";

/**
 * Get the stored Anthropic API key from sessionStorage
 */
export function getStoredApiKey(): string | null {
  return sessionStorage.getItem(API_KEY_STORAGE_KEY);
}

/**
 * Store the Anthropic API key in sessionStorage
 */
export function storeApiKey(apiKey: string): void {
  sessionStorage.setItem(API_KEY_STORAGE_KEY, apiKey);
}

/**
 * Clear the stored API key
 */
export function clearApiKey(): void {
  sessionStorage.removeItem(API_KEY_STORAGE_KEY);
}

/**
 * Check if API key is already stored
 */
export function hasStoredApiKey(): boolean {
  return getStoredApiKey() !== null;
}
