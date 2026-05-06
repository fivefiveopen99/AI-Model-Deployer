import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/components/Layout.vue'
import Dashboard from '@/views/Dashboard.vue'
import Models from '@/views/Models.vue'
import ModelDetail from '@/views/ModelDetail.vue'
import Deployments from '@/views/Deployments.vue'
import DeploymentDetail from '@/views/DeploymentDetail.vue'
import ModelPlayground from '@/views/ModelPlayground.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: Dashboard
      },
      {
        path: 'models',
        name: 'Models',
        component: Models
      },
      {
        path: 'models/:id',
        name: 'ModelDetail',
        component: ModelDetail
      },
      {
        path: 'deployments',
        name: 'Deployments',
        component: Deployments
      },
      {
        path: 'deployments/:id',
        name: 'DeploymentDetail',
        component: DeploymentDetail
      },
      {
        path: 'deployments/:id/playground',
        name: 'ModelPlayground',
        component: ModelPlayground
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
