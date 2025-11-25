<template>
  <div>
    <div class="user-info">
      <div>
        <p>Logged in as <strong>{{ user.name }}</strong></p>
        <p v-if="user.email"><small>{{ user.email }}</small></p>
      </div>
      <button class="secondary" @click="emit('logout')">Logout</button>
    </div>

    <h1>File Manager</h1>

    <div v-if="message.text" :class="['message', message.type]">
      {{ message.text }}
    </div>

    <div class="actions">
      <!-- Upload Section -->
      <div class="action-card">
        <h3>Upload File</h3>
        <form @submit.prevent="handleUpload">
          <div class="form-group">
            <label for="file">Choose file</label>
            <input
              type="file"
              id="file"
              ref="fileInput"
              @change="handleFileSelect"
              :disabled="uploading"
            />
          </div>
          <button type="submit" :disabled="!selectedFile || uploading">
            {{ uploading ? 'Uploading...' : 'Upload' }}
          </button>
        </form>
      </div>

      <!-- Download Section -->
      <div class="action-card">
        <h3>Download File</h3>
        <div class="form-group">
          <label for="download-select">Select file</label>
          <select
            id="download-select"
            v-model="selectedDownloadFile"
            :disabled="downloading || activeFiles.length === 0"
          >
            <option value="">{{ activeFiles.length === 0 ? 'No files available' : 'Choose a file...' }}</option>
            <option v-for="file in activeFiles" :key="file.filename" :value="file.filename">
              {{ file.filename }} ({{ formatSize(file.size) }})
            </option>
          </select>
        </div>
        <button
          @click="handleDownload"
          :disabled="!selectedDownloadFile || downloading"
        >
          {{ downloading ? 'Downloading...' : 'Download' }}
        </button>
      </div>
    </div>

    <!-- Active Files List -->
    <div class="file-list">
      <h3>Your Files ({{ activeFiles.length }})</h3>
      <div v-if="loadingFiles" class="loading">Loading files...</div>
      <div v-else-if="activeFiles.length === 0" class="empty-state">
        No files yet. Upload your first file above!
      </div>
      <div v-else>
        <div v-for="file in activeFiles" :key="file.filename" class="file-item">
          <div>
            <span>{{ file.filename }}</span>
            <small>{{ formatSize(file.size) }}</small>
          </div>
          <button class="secondary" @click="handleDelete(file.filename)" :disabled="deleting">
            Delete
          </button>
        </div>
      </div>
    </div>

    <!-- Deleted Files List -->
    <div v-if="deletedFiles.length > 0" class="file-list deleted-section">
      <h3>Deleted Files ({{ deletedFiles.length }})</h3>
      <p class="info-text">These files have been deleted and cannot be downloaded. You cannot upload files with these names.</p>
      <div>
        <div v-for="file in deletedFiles" :key="file.filename" class="file-item deleted">
          <div>
            <span>{{ file.filename }}</span>
            <small>{{ formatSize(file.size) }}</small>
            <small class="deleted-label">Deleted</small>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  user: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['logout'])

const API_BASE = '/fileshare'

const files = ref([])
const loadingFiles = ref(false)
const selectedFile = ref(null)
const selectedDownloadFile = ref('')
const uploading = ref(false)
const downloading = ref(false)
const deleting = ref(false)
const message = ref({ text: '', type: '' })
const fileInput = ref(null)

// Separate active and deleted files
const activeFiles = computed(() => files.value.filter(f => !f.deleted))
const deletedFiles = computed(() => files.value.filter(f => f.deleted))

const loadFiles = async () => {
  loadingFiles.value = true
  try {
    const response = await fetch(`${API_BASE}/persons/${encodeURIComponent(props.user.name)}/files`)
    if (response.ok) {
      const data = await response.json()
      // Extract files from response and flatten properties
      files.value = (data.files || []).map(file => ({
        filename: file.properties?.filename || file.filename,
        size: file.properties?.size || file.size,
        content_type: file.properties?.content_type || file.content_type,
        deleted: file.properties?.deleted || file.deleted
      }))
    } else {
      console.error('Failed to load files')
    }
  } catch (error) {
    console.error('Error loading files:', error)
  } finally {
    loadingFiles.value = false
  }
}

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  selectedFile.value = file || null
}

const handleUpload = async () => {
  if (!selectedFile.value) return

  uploading.value = true
  message.value = { text: '', type: '' }

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('person', props.user.name)

    const response = await fetch(`${API_BASE}/files/upload`, {
      method: 'POST',
      body: formData,
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
      const error = await response.json()
      message.value = {
        text: error.error || 'Upload failed',
        type: 'error'
      }
    }
  } catch (error) {
    console.error('Upload error:', error)
    message.value = {
      text: 'Upload failed. Please try again.',
      type: 'error'
    }
  } finally {
    uploading.value = false
  }
}

const handleDownload = async () => {
  if (!selectedDownloadFile.value) return

  downloading.value = true
  message.value = { text: '', type: '' }

  try {
    const response = await fetch(
      `${API_BASE}/files/${encodeURIComponent(props.user.name)}/${encodeURIComponent(selectedDownloadFile.value)}/download`
    )

    if (response.ok) {
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = selectedDownloadFile.value
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

      message.value = {
        text: `Successfully downloaded ${selectedDownloadFile.value}`,
        type: 'success'
      }
      selectedDownloadFile.value = ''
      await loadFiles()
    } else {
      const error = await response.json()
      message.value = {
        text: error.error || 'Download failed',
        type: 'error'
      }
    }
  } catch (error) {
    console.error('Download error:', error)
    message.value = {
      text: 'Download failed. Please try again.',
      type: 'error'
    }
  } finally {
    downloading.value = false
  }
}

const handleDelete = async (filename) => {
  if (!confirm(`Are you sure you want to delete ${filename}?`)) return

  deleting.value = true
  message.value = { text: '', type: '' }

  try {
    const response = await fetch(
      `${API_BASE}/files/${encodeURIComponent(props.user.name)}/${encodeURIComponent(filename)}`,
      {
        method: 'DELETE',
      }
    )

    if (response.ok) {
      message.value = {
        text: `Successfully deleted ${filename}`,
        type: 'success'
      }
      await loadFiles()
    } else {
      const error = await response.json()
      message.value = {
        text: error.error || 'Delete failed',
        type: 'error'
      }
    }
  } catch (error) {
    console.error('Delete error:', error)
    message.value = {
      text: 'Delete failed. Please try again.',
      type: 'error'
    }
  } finally {
    deleting.value = false
  }
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

onMounted(() => {
  loadFiles()
})
</script>
