import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import 'primevue/resources/themes/lara-light-blue/theme.css'
import 'primevue/resources/primevue.min.css'
import 'primeicons/primeicons.css'

import App from './App.vue'
import './index.css'

const app = createApp(App)

app.use(PrimeVue, {
  unstyled: false,
  pt: {},
})

app.mount('#app')
