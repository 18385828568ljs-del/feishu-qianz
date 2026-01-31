import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn } from './services/api'

// 路由懒加载
const Dashboard = () => import('./views/Dashboard.vue')
const Users = () => import('./views/Users.vue')
const Forms = () => import('./views/Forms.vue')
const Invites = () => import('./views/Invites.vue')
const Logs = () => import('./views/Logs.vue')
const Login = () => import('./views/Login.vue')

const routes = [
    {
        path: '/login',
        name: 'Login',
        component: Login,
        meta: { requiresAuth: false }
    },
    {
        path: '/',
        name: 'Dashboard',
        component: Dashboard,
        meta: { title: '仪表盘', icon: 'Odometer' }
    },
    {
        path: '/users',
        name: 'Users',
        component: Users,
        meta: { title: '用户管理', icon: 'User' }
    },
    {
        path: '/forms',
        name: 'Forms',
        component: Forms,
        meta: { title: '表单管理', icon: 'Document' }
    },
    {
        path: '/invites',
        name: 'Invites',
        component: Invites,
        meta: { title: '邀请码', icon: 'Ticket' }
    },
    {
        path: '/orders',
        name: 'Orders',
        component: () => import('./views/Orders.vue'),
        meta: { title: '订单管理', icon: 'ShoppingCart' }
    },
    {
        path: '/pricing',
        name: 'Pricing',
        component: () => import('./views/Pricing.vue'),
        meta: { title: '定价方案', icon: 'PriceTag' }
    },
    {
        path: '/logs',
        name: 'Logs',
        component: Logs,
        meta: { title: '签名日志', icon: 'List' }
    }
]

const router = createRouter({
    // 开发环境使用根路径，生产环境使用 /admin-panel/
    history: createWebHistory(import.meta.env.BASE_URL),
    routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
    if (to.meta.requiresAuth !== false && !isLoggedIn()) {
        next('/login')
    } else {
        next()
    }
})

export default router
export { routes }
