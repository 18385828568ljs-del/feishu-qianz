import { createRouter, createWebHistory } from 'vue-router'
import Form from './components/Form/index.vue'
import SignPage from './components/SignPage.vue'

const routes = [
    {
        path: '/',
        name: 'Home',
        component: Form
    },
    {
        path: '/sign',
        name: 'Sign',
        component: SignPage
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router
