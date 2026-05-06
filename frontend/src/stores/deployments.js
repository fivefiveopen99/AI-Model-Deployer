import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { deploymentsApi } from '@/api'

export const useDeploymentsStore = defineStore('deployments', () => {
  // State
  const deployments = ref([])
  const currentDeployment = ref(null)
  const loading = ref(false)
  const total = ref(0)
  const logs = ref('')

  // Getters
  const deploymentList = computed(() => deployments.value)
  const isLoading = computed(() => loading.value)

  // Actions
  const fetchDeployments = async (params = {}) => {
    loading.value = true
    try {
      const response = await deploymentsApi.getList(params)
      deployments.value = response.data.items
      total.value = response.data.total
      return response.data
    } catch (error) {
      console.error('Failed to fetch deployments:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const fetchDeploymentDetail = async (id) => {
    loading.value = true
    try {
      const response = await deploymentsApi.getDetail(id)
      currentDeployment.value = response.data
      return response.data
    } catch (error) {
      console.error('Failed to fetch deployment detail:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const createDeployment = async (data) => {
    try {
      const response = await deploymentsApi.create(data)
      return response.data
    } catch (error) {
      console.error('Failed to create deployment:', error)
      throw error
    }
  }

  const deployToK8s = async (id) => {
    try {
      const response = await deploymentsApi.deploy(id)
      return response.data
    } catch (error) {
      console.error('Failed to deploy:', error)
      throw error
    }
  }

  const scaleDeployment = async (id, replicas) => {
    try {
      const response = await deploymentsApi.scale(id, replicas)
      return response.data
    } catch (error) {
      console.error('Failed to scale deployment:', error)
      throw error
    }
  }

  const deleteDeployment = async (id) => {
    try {
      await deploymentsApi.delete(id)
      deployments.value = deployments.value.filter(d => d.id !== id)
    } catch (error) {
      console.error('Failed to delete deployment:', error)
      throw error
    }
  }

  const getDeploymentStatus = async (id) => {
    try {
      const response = await deploymentsApi.getStatus(id)
      return response.data
    } catch (error) {
      console.error('Failed to get deployment status:', error)
      throw error
    }
  }

  const getDeploymentLogs = async (id, tailLines = 100) => {
    try {
      const response = await deploymentsApi.getLogs(id, tailLines)
      logs.value = response.data.logs
      return response.data
    } catch (error) {
      console.error('Failed to get deployment logs:', error)
      throw error
    }
  }

  const getK8sDeployments = async (namespace) => {
    try {
      const response = await deploymentsApi.getK8sList(namespace)
      return response.data
    } catch (error) {
      console.error('Failed to get K8s deployments:', error)
      throw error
    }
  }

  return {
    deployments,
    currentDeployment,
    loading,
    total,
    logs,
    deploymentList,
    isLoading,
    fetchDeployments,
    fetchDeploymentDetail,
    createDeployment,
    deployToK8s,
    scaleDeployment,
    deleteDeployment,
    getDeploymentStatus,
    getDeploymentLogs,
    getK8sDeployments
  }
})
