import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/components/Layout.vue'
import Dashboard from '@/views/Dashboard.vue'
import Models from '@/views/Models.vue'
import ModelDetail from '@/views/ModelDetail.vue'
import Deployments from '@/views/Deployments.vue'
import DeploymentDetail from '@/views/DeploymentDetail.vue'
import DeploymentInference from '@/views/DeploymentInference.vue'
import ModelPlayground from '@/views/ModelPlayground.vue'
import RegistryImages from '@/views/RegistryImages.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    meta: {
      navLabel: '控制台'
    },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: Dashboard,
        meta: {
          navLabel: '总览',
          navDescription: '系统状态与工作台'
        }
      },
      {
        path: 'models',
        name: 'Models',
        component: Models,
        meta: {
          navLabel: '模型管理',
          navDescription: '导入、构建与资产状态'
        }
      },
      {
        path: 'models/:id',
        name: 'ModelDetail',
        component: ModelDetail,
        meta: {
          navLabel: '模型详情',
          navDescription: '模型配置与构建信息'
        }
      },
      {
        path: 'deployments',
        name: 'Deployments',
        component: Deployments,
        meta: {
          navLabel: '部署管理',
          navDescription: '部署记录、资源与访问入口'
        }
      },
      {
        path: 'deployments/:id',
        name: 'DeploymentDetail',
        component: DeploymentDetail,
        meta: {
          navLabel: '部署详情',
          navDescription: 'Kubernetes 状态与运行信息'
        }
      },
      {
        path: 'deployments/:id/inference',
        name: 'DeploymentInference',
        component: DeploymentInference,
        meta: {
          navLabel: '命令工作台',
          navDescription: '镜像命令模板与结果浏览'
        }
      },
      {
        path: 'deployments/:id/playground',
        name: 'ModelPlayground',
        component: ModelPlayground,
        meta: {
          navLabel: '模型交互测试',
          navDescription: '请求、预览与结果分析'
        }
      },
      {
        path: 'images',
        name: 'RegistryImages',
        component: RegistryImages,
        meta: {
          navLabel: '镜像仓库',
          navDescription: 'Registry 镜像浏览与导入'
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
