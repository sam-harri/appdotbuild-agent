<template>
  <div class="min-h-screen bg-white dark:bg-black text-black dark:text-white transition-colors duration-300 ease-in-out p-5">
    <!-- Background gradient -->
    <div class="fixed inset-0 bg-gradient-to-br from-gray-50/30 to-transparent dark:from-white/5 dark:to-transparent -z-20 transition-all duration-300"></div>
    
    <!-- Background grid -->
    <div class="fixed inset-0 bg-[linear-gradient(to_right,rgba(0,0,0,0.05)_1px,transparent_1px),linear-gradient(to_bottom,rgba(0,0,0,0.05)_1px,transparent_1px)] dark:bg-[linear-gradient(to_right,rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[length:24px_24px] -z-10 transition-all duration-300"></div>
    
    <!-- Main content -->
    <div class="flex items-center justify-center min-h-screen">
      <div class="text-center max-w-2xl">
        <h1 class="text-5xl font-bold mb-4 tracking-tight text-gray-900 dark:text-white">
          Under Construction
        </h1>
        <p class="text-xl text-gray-600 dark:text-gray-300 mb-8 leading-relaxed">
          Your app is under construction. It's being built right now!
        </p>
        
        <!-- Animated dots -->
        <div class="flex justify-center gap-1 mt-8">
          <div class="w-1 h-1 bg-gray-900 dark:bg-white rounded-full animate-pulse" style="animation-delay: -0.32s; animation-duration: 1.4s;"></div>
          <div class="w-1 h-1 bg-gray-900 dark:bg-white rounded-full animate-pulse" style="animation-delay: -0.16s; animation-duration: 1.4s;"></div>
          <div class="w-1 h-1 bg-gray-900 dark:bg-white rounded-full animate-pulse" style="animation-duration: 1.4s;"></div>
        </div>
        
        <!-- Footer -->
        <footer class="fixed bottom-5 left-1/2 transform -translate-x-1/2 text-sm text-gray-500 dark:text-gray-400">
          Built with ❤️ by
          <a href="https://app.build" target="_blank" class="text-gray-900 dark:text-white font-semibold hover:underline transition-colors">
            app.build
          </a>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { api } from './utils/api'

onMounted(async () => {
  try {
    const data = await api.healthcheck()
    console.log(data)
  } catch (error) {
    console.error('Healthcheck failed:', error)
  }
})
</script>
