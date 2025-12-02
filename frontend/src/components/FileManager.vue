<template>
  <div>
    <div class="user-info" role="banner">
      <div>
        <p>Logged in as <strong>{{ user.name }}</strong></p>
        <p v-if="user.email"><small>{{ user.email }}</small></p>
      </div>
      <button class="secondary" @click="emit('logout')" aria-label="Logout from file manager">
        Logout
      </button>
    </div>

    <h1>File Manager</h1>

    <div class="tabs" role="tablist">
      <button
        role="tab"
        :class="['tab', { active: activeTab === 'files' }]"
        :aria-selected="activeTab === 'files'"
        @click="activeTab = 'files'"
      >
        Files
      </button>
      <button
        role="tab"
        :class="['tab', { active: activeTab === 'calculator' }]"
        :aria-selected="activeTab === 'calculator'"
        @click="activeTab = 'calculator'"
      >
        Calculator
      </button>
    </div>

    <div
      v-if="message.text"
      :class="['message', message.type]"
      role="alert"
      :aria-live="message.type === 'error' ? 'assertive' : 'polite'"
    >
      {{ message.text }}
    </div>

    <div v-show="activeTab === 'files'" class="tab-content">
    <div class="actions">
      <section class="action-card" aria-labelledby="upload-heading">
        <h3 id="upload-heading">Upload File</h3>
        <form @submit.prevent="handleUpload" aria-label="File upload form">
          <div class="form-group">
            <label for="file">Choose file</label>
            <input
              type="file"
              id="file"
              ref="fileInput"
              @change="handleFileSelect"
              :disabled="uploading"
              :aria-busy="uploading"
            />
          </div>
          <button type="submit" :disabled="!selectedFile || uploading" :aria-busy="uploading">
            {{ uploading ? 'Uploading...' : 'Upload' }}
          </button>
        </form>
      </section>

      <section class="action-card" aria-labelledby="download-heading">
        <h3 id="download-heading">Download File</h3>
        <div class="form-group">
          <label for="download-select">Select file</label>
          <select
            id="download-select"
            v-model="selectedDownloadFile"
            :disabled="downloading || activeFiles.length === 0"
            :aria-busy="downloading"
          >
            <option value="">{{ activeFiles.length === 0 ? 'No files available' : 'Choose a file...' }}</option>
            <option v-for="file in activeFiles" :key="file.filename" :value="file.filename">
              {{ file.filename }} ({{ formatFileSize(file.size) }})
            </option>
          </select>
        </div>
        <button
          @click="handleDownload"
          :disabled="!selectedDownloadFile || downloading"
          :aria-busy="downloading"
          aria-label="Download selected file"
        >
          {{ downloading ? 'Downloading...' : 'Download' }}
        </button>
      </section>
    </div>

    <section class="file-list" aria-labelledby="files-heading">
      <h3 id="files-heading">Your Files ({{ activeFiles.length }})</h3>
      <div v-if="loadingFiles" class="loading" role="status" aria-live="polite">
        Loading files...
      </div>
      <div v-else-if="activeFiles.length === 0" class="empty-state">
        No files yet. Upload your first file above!
      </div>
      <ul v-else role="list" class="file-items-list">
        <li v-for="file in activeFiles" :key="file.filename" class="file-item">
          <div>
            <span>{{ file.filename }}</span>
            <small>{{ formatFileSize(file.size) }}</small>
          </div>
          <div class="file-actions">
            <button
              v-if="isEditableFile(file)"
              @click="handleEdit(file.filename)"
              :disabled="editing"
              :aria-busy="editing"
              class="edit-btn"
              :aria-label="`Edit ${file.filename}`"
            >
              Edit
            </button>
            <button
              class="secondary"
              @click="handleDelete(file.filename)"
              :disabled="deletingFiles.has(file.filename)"
              :aria-busy="deletingFiles.has(file.filename)"
              :aria-label="`Delete ${file.filename}`"
            >
              Delete
            </button>
          </div>
        </li>
      </ul>
    </section>

    <section v-if="deletedFiles.length > 0" class="file-list deleted-section" aria-labelledby="deleted-files-heading">
      <h3 id="deleted-files-heading">Deleted Files ({{ deletedFiles.length }})</h3>
      <p class="info-text">These files have been deleted and cannot be downloaded. You cannot upload files with these names.</p>
      <ul role="list" class="file-items-list">
        <li v-for="file in deletedFiles" :key="file.filename" class="file-item deleted">
          <div>
            <span>{{ file.filename }}</span>
            <small>{{ formatFileSize(file.size) }}</small>
            <small class="deleted-label">Deleted</small>
          </div>
        </li>
      </ul>
    </section>

    <div
      v-if="editingFile"
      class="modal-overlay"
      @click="closeEditor"
      role="dialog"
      aria-modal="true"
      aria-labelledby="editor-title"
    >
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2 id="editor-title">Edit {{ editingFile }}</h2>
          <button
            class="close-btn"
            @click="closeEditor"
            aria-label="Close editor"
          >
            &times;
          </button>
        </div>
        <div class="modal-body">
          <label for="file-editor" class="visually-hidden">File content editor</label>
          <textarea
            id="file-editor"
            v-model="fileContent"
            class="file-editor"
            :disabled="saving"
            :aria-busy="saving"
          ></textarea>
        </div>
        <div class="modal-footer">
          <button class="secondary" @click="closeEditor" :disabled="saving">
            Cancel
          </button>
          <button @click="saveEdit" :disabled="saving" :aria-busy="saving">
            {{ saving ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </div>
    </div>
    </div>

    <div v-show="activeTab === 'calculator'" class="tab-content">
      <Calculator />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { API_BASE, extractFileData, handleApiError, apiRequest } from '../utils/api.js'
import { formatFileSize } from '../utils/format.js'
import { isEditableFile, triggerDownload } from '../utils/file.js'
import Calculator from './Calculator.vue'

const props = defineProps({
  user: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['logout'])

const activeTab = ref('calculator')
const files = ref([])
const loadingFiles = ref(false)
const selectedFile = ref(null)
const selectedDownloadFile = ref('')
const uploading = ref(false)
const downloading = ref(false)
const deletingFiles = ref(new Set())
const editing = ref(false)
const saving = ref(false)
const editingFile = ref(null)
const fileContent = ref('')
const originalContentType = ref('')
const message = ref({ text: '', type: '' })
const fileInput = ref(null)

const activeFiles = computed(() => files.value.filter(f => !f.deleted))
const deletedFiles = computed(() => files.value.filter(f => f.deleted))

/**
 * Loads all files for the current user
 */
const loadFiles = async () => {
  loadingFiles.value = true
  message.value = { text: '', type: '' }

  try {
    const response = await apiRequest(
      `${API_BASE}/persons/${encodeURIComponent(props.user.name)}/files`
    )

    if (response.ok) {
      const data = await response.json()
      files.value = (data.files || []).map(extractFileData)
    } else {
      const errorMsg = await handleApiError(null, response, 'Failed to load files')
      message.value = { text: errorMsg, type: 'error' }
    }
  } catch (error) {
    console.error('Error loading files:', error)
    const errorMsg = await handleApiError(error)
    message.value = { text: errorMsg, type: 'error' }
  } finally {
    loadingFiles.value = false
  }
}

/**
 * Handles file selection from input
 */
const handleFileSelect = (event) => {
  const file = event.target.files[0]
  selectedFile.value = file || null
}

/**
 * Handles file upload to the server
 */
const handleUpload = async () => {
  if (!selectedFile.value) return

  uploading.value = true
  message.value = { text: '', type: '' }

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('person', props.user.name)

    const response = await apiRequest(`${API_BASE}/files/upload`, {
      method: 'POST',
      body: formData
    })

    if (response.ok) {
      message.value = {
        text: `Successfully uploaded ${selectedFile.value.name}`,
        type: 'success'
      }
      selectedFile.value = null
      if (fileInput.value) {
        fileInput.value.value = ''
      }
      await loadFiles()
    } else {
      const errorMsg = await handleApiError(null, response, 'Upload failed')
      message.value = { text: errorMsg, type: 'error' }
    }
  } catch (error) {
    console.error('Upload error:', error)
    const errorMsg = await handleApiError(error, null, 'Upload failed. Please try again.')
    message.value = { text: errorMsg, type: 'error' }
  } finally {
    uploading.value = false
  }
}

/**
 * Handles file download from the server
 */
const handleDownload = async () => {
  if (!selectedDownloadFile.value) return

  downloading.value = true
  message.value = { text: '', type: '' }

  try {
    const response = await apiRequest(
      `${API_BASE}/files/${encodeURIComponent(props.user.name)}/${encodeURIComponent(selectedDownloadFile.value)}/download`
    )

    if (response.ok) {
      const blob = await response.blob()
      triggerDownload(blob, selectedDownloadFile.value)

      message.value = {
        text: `Successfully downloaded ${selectedDownloadFile.value}`,
        type: 'success'
      }
      selectedDownloadFile.value = ''
      await loadFiles()
    } else {
      const errorMsg = await handleApiError(null, response, 'Download failed')
      message.value = { text: errorMsg, type: 'error' }
    }
  } catch (error) {
    console.error('Download error:', error)
    const errorMsg = await handleApiError(error, null, 'Download failed. Please try again.')
    message.value = { text: errorMsg, type: 'error' }
  } finally {
    downloading.value = false
  }
}

/**
 * Handles file deletion with user confirmation
 */
const handleDelete = async (filename) => {
  if (deletingFiles.value.has(filename)) return
  if (!confirm(`Are you sure you want to delete ${filename}?`)) return

  deletingFiles.value.add(filename)
  message.value = { text: '', type: '' }

  try {
    const response = await apiRequest(
      `${API_BASE}/files/${encodeURIComponent(props.user.name)}/${encodeURIComponent(filename)}`,
      { method: 'DELETE' }
    )

    if (response.ok) {
      message.value = {
        text: `Successfully deleted ${filename}`,
        type: 'success'
      }
      await loadFiles()
    } else {
      const errorMsg = await handleApiError(null, response, 'Delete failed')
      message.value = { text: errorMsg, type: 'error' }
    }
  } catch (error) {
    console.error('Delete error:', error)
    const errorMsg = await handleApiError(error, null, 'Delete failed. Please try again.')
    message.value = { text: errorMsg, type: 'error' }
  } finally {
    deletingFiles.value.delete(filename)
  }
}

/**
 * Opens file editor and loads file content
 */
const handleEdit = async (filename) => {
  editing.value = true
  message.value = { text: '', type: '' }

  try {
    const file = activeFiles.value.find(f => f.filename === filename)
    if (file) {
      originalContentType.value = file.content_type
    }

    const response = await apiRequest(
      `${API_BASE}/files/${encodeURIComponent(props.user.name)}/${encodeURIComponent(filename)}/download`
    )

    if (response.ok) {
      const text = await response.text()
      fileContent.value = text
      editingFile.value = filename
    } else {
      const errorMsg = await handleApiError(null, response, 'Failed to load file')
      message.value = { text: errorMsg, type: 'error' }
    }
  } catch (error) {
    console.error('Edit error:', error)
    const errorMsg = await handleApiError(error, null, 'Failed to load file. Please try again.')
    message.value = { text: errorMsg, type: 'error' }
  } finally {
    editing.value = false
  }
}

/**
 * Saves edited file content to the server
 */
const saveEdit = async () => {
  if (!editingFile.value) return

  saving.value = true
  message.value = { text: '', type: '' }

  try {
    const contentType = originalContentType.value || 'text/plain'
    const blob = new Blob([fileContent.value], { type: contentType })
    const file = new File([blob], editingFile.value, { type: contentType })

    const formData = new FormData()
    formData.append('file', file)

    const response = await apiRequest(
      `${API_BASE}/files/${encodeURIComponent(props.user.name)}/${encodeURIComponent(editingFile.value)}`,
      {
        method: 'PUT',
        body: formData
      }
    )

    if (response.ok) {
      message.value = {
        text: `Successfully saved ${editingFile.value}`,
        type: 'success'
      }
      closeEditor()
      await loadFiles()
    } else {
      const errorMsg = await handleApiError(null, response, 'Save failed')
      message.value = { text: errorMsg, type: 'error' }
    }
  } catch (error) {
    console.error('Save error:', error)
    const errorMsg = await handleApiError(error, null, 'Save failed. Please try again.')
    message.value = { text: errorMsg, type: 'error' }
  } finally {
    saving.value = false
  }
}

/**
 * Closes the file editor modal
 */
const closeEditor = () => {
  editingFile.value = null
  fileContent.value = ''
  originalContentType.value = ''
}

onMounted(() => {
  loadFiles()
})
</script>

<style scoped>
.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #e0e0e0;
}

.tab {
  padding: 0.75rem 1.5rem;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  color: #666;
  transition: all 0.2s ease;
  margin-bottom: -2px;
}

.tab:hover {
  color: #333;
  background-color: #f5f5f5;
}

.tab.active {
  color: #1976d2;
  border-bottom-color: #1976d2;
  font-weight: 600;
}

.tab-content {
  animation: fadeIn 0.2s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
