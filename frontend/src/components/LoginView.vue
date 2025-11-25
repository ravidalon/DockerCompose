<template>
  <div>
    <h1>File Share</h1>
    <h2>Welcome! Please enter your name to continue</h2>

    <div v-if="message.text" :class="['message', message.type]">
      {{ message.text }}
    </div>

    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="name">Your Name</label>
        <input
          type="text"
          id="name"
          v-model="name"
          placeholder="Enter your name"
          required
          :disabled="loading"
        />
      </div>

      <div class="form-group">
        <label for="email">Email (optional)</label>
        <input
          type="email"
          id="email"
          v-model="email"
          placeholder="your.email@example.com"
          :disabled="loading"
        />
      </div>

      <button type="submit" :disabled="loading || !name.trim()">
        {{ loading ? 'Loading...' : 'Continue' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['login'])

const name = ref('')
const email = ref('')
const loading = ref(false)
const message = ref({ text: '', type: '' })

const API_BASE = '/fileshare'

const handleSubmit = async () => {
  loading.value = true
  message.value = { text: '', type: '' }

  try {
    // Try to get existing person
    const getResponse = await fetch(`${API_BASE}/persons/${encodeURIComponent(name.value)}`)

    if (getResponse.ok) {
      const person = await getResponse.json()
      // Extract properties from Neo4j response structure
      const userData = {
        name: person.properties?.name || person.name,
        email: person.properties?.email || person.email
      }
      emit('login', userData)
      return
    }

    // Person doesn't exist, create new one
    if (getResponse.status === 404) {
      const createResponse = await fetch(`${API_BASE}/persons`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name.value,
          email: email.value || `${name.value.toLowerCase().replace(/\s+/g, '.')}@example.com`
        }),
      })

      if (createResponse.ok) {
        const person = await createResponse.json()
        // Extract properties from Neo4j response structure
        const userData = {
          name: person.properties?.name || person.name,
          email: person.properties?.email || person.email
        }
        emit('login', userData)
        return
      }

      const error = await createResponse.json()
      message.value = {
        text: error.error || 'Failed to create user',
        type: 'error'
      }
    } else {
      message.value = {
        text: 'Failed to check user',
        type: 'error'
      }
    }
  } catch (error) {
    console.error('Login error:', error)
    message.value = {
      text: 'Network error. Please check if services are running.',
      type: 'error'
    }
  } finally {
    loading.value = false
  }
}
</script>
