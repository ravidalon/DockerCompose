/**
 * API utilities for interacting with the fileshare backend
 */

export const API_BASE = '/fileshare'

/**
 * Extracts person data from API response
 * @param {Object} person - Person object from API
 * @returns {Object} Normalized person data
 */
export function extractPersonData(person) {
  return {
    name: person.properties?.name || person.name,
    email: person.properties?.email || person.email
  }
}

/**
 * Extracts file data from API response
 * @param {Object} file - File object from API
 * @returns {Object} Normalized file data
 */
export function extractFileData(file) {
  return {
    filename: file.properties?.filename || file.filename,
    size: file.properties?.size || file.size,
    content_type: file.properties?.content_type || file.content_type,
    deleted: file.properties?.deleted || file.deleted
  }
}

/**
 * Handles API errors and returns a user-friendly message
 * @param {Error} error - The error object
 * @param {Response} [response] - Optional response object
 * @param {string} [defaultMessage='An error occurred'] - Default message if parsing fails
 * @returns {Promise<string>} Error message
 */
export async function handleApiError(error, response = null, defaultMessage = 'An error occurred') {
  if (response && !response.ok) {
    try {
      const data = await response.json()
      return data.error || defaultMessage
    } catch {
      return defaultMessage
    }
  }

  if (error.message === 'Failed to fetch') {
    return 'Network error. Please check if services are running.'
  }

  return error.message || defaultMessage
}

/**
 * Makes an API request with consistent error handling
 * @param {string} url - API endpoint URL
 * @param {RequestInit} [options={}] - Fetch options
 * @returns {Promise<Response>} Response object
 * @throws {Error} If request fails
 */
export async function apiRequest(url, options = {}) {
  try {
    const response = await fetch(url, options)
    return response
  } catch (error) {
    console.error('API request failed:', error)
    throw error
  }
}
