import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { systemApi } from '@/api'

export const useSystemStore = defineStore('system', () => {
  // State
  const status = ref({
    docker_connected: false,
    k8s_connected: false,
    total_models: 0,
    total_deployments: 0,
    running_deployments: 0
  })
  const loading = ref(false)

  // Getters
  const systemStatus = computed(() => status.value)
  const isDockerConnected = computed(() => status.value.docker_connected)
  const isK8sConnected = computed(() => status.value.k8s_connected)
  const isLoading = computed(() => loading.value)

  // Actions
  const fetchStatus = async () => {
    loading.value = true
    try {
      const response = await systemApi.getStatus()
      status.value = response.data
      return response.data
    } catch (error) {
      console.error('Failed to fetch system status:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  return {
    status,
    loading,
    systemStatus,
    isDockerConnected,
    isK8sConnected,
    isLoading,
    fetchStatus
  }
})
