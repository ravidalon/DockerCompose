/**
 * Formatting utilities
 */

/**
 * Formats byte size into human-readable format
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size string
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes'

  const units = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  const size = bytes / Math.pow(k, i)

  return `${Math.round(size * 100) / 100} ${units[i]}`
}

/**
 * Generates a default email from a name
 * @param {string} name - Person's name
 * @returns {string} Generated email address
 */
export function generateDefaultEmail(name) {
  const normalized = name.toLowerCase().replace(/\s+/g, '.')
  return `${normalized}@example.com`
}
