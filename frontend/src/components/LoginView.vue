<template>
  <div>
    <h1>File Share</h1>
    <h2>Welcome! Please enter your name to continue</h2>

    <div
      v-if="message.text"
      :class="['message', message.type]"
      role="alert"
      :aria-live="message.type === 'error' ? 'assertive' : 'polite'"
    >
      {{ message.text }}
    </div>

    <form @submit.prevent="handleSubmit" aria-label="Login form">
      <div class="form-group">
        <label for="name">
          Your Name
          <span class="required-indicator" aria-label="required">*</span>
        </label>
        <input
          type="text"
          id="name"
          v-model="name"
          placeholder="Enter your name"
          required
          :disabled="loading"
          :aria-invalid="!name.trim() && name.length > 0"
          aria-describedby="name-hint"
        />
        <small id="name-hint" class="form-hint">This name will be used to identify you</small>
      </div>

      <div class="form-group">
        <label for="email">Email (optional)</label>
        <input
          type="email"
          id="email"
          v-model="email"
          placeholder="your.email@example.com"
          :disabled="loading"
          aria-describedby="email-hint"
        />
        <small id="email-hint" class="form-hint">We'll generate one for you if left blank</small>
      </div>

      <button
        type="submit"
        :disabled="loading || !name.trim()"
        :aria-busy="loading"
      >
        {{ loading ? 'Loading...' : 'Continue' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { API_BASE, extractPersonData, handleApiError, apiRequest } from '../utils/api.js'
import { generateDefaultEmail } from '../utils/format.js'

const emit = defineEmits(['login'])

const name = ref('')
const email = ref('')
const loading = ref(false)
const message = ref({ text: '', type: '' })

/**
 * Handles login form submission
 * Attempts to fetch existing user or create new one
 */
const handleSubmit = async () => {
  loading.value = true
  message.value = { text: '', type: '' }

  try {
    // Try to fetch existing user
    const getResponse = await apiRequest(
      `${API_BASE}/persons/${encodeURIComponent(name.value)}`
    )

    if (getResponse.ok) {
      const person = await getResponse.json()
      emit('login', extractPersonData(person))
      return
    }

    // Create new user if not found
    if (getResponse.status === 404) {
      const createResponse = await apiRequest(`${API_BASE}/persons`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.value,
          email: email.value || generateDefaultEmail(name.value)
        })
      })

      if (createResponse.ok) {
        const person = await createResponse.json()
        emit('login', extractPersonData(person))
        return
      }

      const errorMsg = await handleApiError(null, createResponse, 'Failed to create user')
      message.value = { text: errorMsg, type: 'error' }
      return
    }

    // Handle other errors
    message.value = {
      text: 'Failed to check user. Please try again.',
      type: 'error'
    }
  } catch (error) {
    console.error('Login error:', error)
    const errorMsg = await handleApiError(error)
    message.value = { text: errorMsg, type: 'error' }
  } finally {
    loading.value = false
  }
}
</script>
