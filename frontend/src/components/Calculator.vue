<template>
  <section class="action-card calculator-card" aria-labelledby="calculator-heading">
    <h3 id="calculator-heading">Calculator</h3>
    <form @submit.prevent="handleCalculate" aria-label="Calculator form">
      <div class="form-group">
        <label for="expression">Enter expression</label>
        <input
          type="text"
          id="expression"
          v-model="expression"
          placeholder="e.g., 2 + 2, sqrt(16), pi * 2"
          :disabled="calculating"
          :aria-busy="calculating"
        />
      </div>
      <button type="submit" :disabled="!expression.trim() || calculating" :aria-busy="calculating">
        {{ calculating ? 'Calculating...' : 'Calculate' }}
      </button>
    </form>

    <div v-if="result !== null" class="result" role="status" aria-live="polite">
      <strong>Result:</strong> {{ result }}
    </div>

    <div v-if="error" class="error-message" role="alert" aria-live="assertive">
      {{ error }}
    </div>

    <details class="help-section">
      <summary>Supported operations</summary>
      <ul class="help-list">
        <li>Basic: +, -, *, /, ** (power, not ^)</li>
        <li>Functions: sqrt(), sin(), cos(), tan(), abs(), round(), min(), max(), sum(), pow()</li>
        <li>Constants: pi, e</li>
        <li>Note: Bitwise operators (^, &, |, ~, <<, >>) are not supported</li>
      </ul>
    </details>
  </section>
</template>

<script setup>
import { ref } from 'vue'

const CALC_BASE = '/calc'

const expression = ref('')
const result = ref(null)
const error = ref('')
const calculating = ref(false)

const handleCalculate = async () => {
  if (!expression.value.trim()) return

  calculating.value = true
  error.value = ''
  result.value = null

  try {
    const response = await fetch(`${CALC_BASE}/calculate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ expression: expression.value })
    })

    const data = await response.json()

    if (response.ok) {
      result.value = data.result
    } else {
      error.value = data.error || 'Calculation failed'
    }
  } catch (err) {
    console.error('Calculation error:', err)
    error.value = 'Failed to connect to calculator service'
  } finally {
    calculating.value = false
  }
}
</script>

<style scoped>
.calculator-card {
  min-height: auto;
}

.result {
  margin-top: 1rem;
  padding: 0.75rem;
  background-color: #e8f5e9;
  border-left: 4px solid #4caf50;
  border-radius: 4px;
  font-size: 1.1rem;
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background-color: #ffebee;
  border-left: 4px solid #f44336;
  border-radius: 4px;
  color: #c62828;
}

.help-section {
  margin-top: 1rem;
  padding: 0.75rem;
  background-color: #f5f5f5;
  border-radius: 4px;
  font-size: 0.9rem;
}

.help-section summary {
  cursor: pointer;
  font-weight: 600;
  user-select: none;
}

.help-section summary:hover {
  color: #1976d2;
}

.help-list {
  margin-top: 0.5rem;
  margin-left: 1.5rem;
  line-height: 1.6;
}

.help-list li {
  margin-bottom: 0.25rem;
}

input[type="text"] {
  font-family: 'Courier New', monospace;
}
</style>
