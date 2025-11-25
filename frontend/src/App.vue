<template>
  <div class="container">
    <LoginView v-if="!currentUser" @login="handleLogin" />
    <FileManager v-else :user="currentUser" @logout="handleLogout" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import LoginView from './components/LoginView.vue'
import FileManager from './components/FileManager.vue'

const currentUser = ref(null)

const handleLogin = (user) => {
  currentUser.value = user
}

const handleLogout = () => {
  currentUser.value = null
}
</script>
