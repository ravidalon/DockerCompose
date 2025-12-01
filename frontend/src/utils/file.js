/**
 * File handling utilities
 */

// Maximum file size for in-browser editing (1MB)
export const MAX_EDITABLE_FILE_SIZE = 1024 * 1024

// Text file content types that can be edited
const TEXT_CONTENT_TYPES = [
  'text/',
  'application/json',
  'application/javascript',
  'application/xml',
  'application/x-sh',
  'application/x-yaml'
]

/**
 * Checks if a file can be edited in the browser
 * @param {Object} file - File object with size and content_type
 * @returns {boolean} True if file is editable
 */
export function isEditableFile(file) {
  if (!file || file.size > MAX_EDITABLE_FILE_SIZE) {
    return false
  }

  return TEXT_CONTENT_TYPES.some(type => file.content_type?.startsWith(type))
}

/**
 * Triggers a download in the browser
 * @param {Blob} blob - File blob to download
 * @param {string} filename - Name for the downloaded file
 */
export function triggerDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')

  anchor.href = url
  anchor.download = filename
  anchor.style.display = 'none'

  document.body.appendChild(anchor)
  anchor.click()

  // Cleanup after a short delay
  setTimeout(() => {
    document.body.removeChild(anchor)
    window.URL.revokeObjectURL(url)
  }, 100)
}
