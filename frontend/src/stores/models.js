import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { modelsApi } from '@/api'

export const useModelsStore = defineStore('models', () => {
  // State
  const models = ref([])
  const currentModel = ref(null)
  const loading = ref(false)
  const total = ref(0)

  // Getters
  const modelList = computed(() => models.value)
  const isLoading = computed(() => loading.value)

  // Actions
  const fetchModels = async (params = {}) => {
    loading.value = true
    try {
      const response = await modelsApi.getList(params)
      models.value = response.data.items
      total.value = response.data.total
      return response.data
    } catch (error) {
      console.error('Failed to fetch models:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const fetchModelDetail = async (id) => {
    loading.value = true
    try {
      const response = await modelsApi.getDetail(id)
      currentModel.value = response.data
      return response.data
    } catch (error) {
      console.error('Failed to fetch model detail:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const createModel = async (data) => {
    try {
      const response = await modelsApi.create(data)
      return response.data
    } catch (error) {
      console.error('Failed to create model:', error)
      throw error
    }
  }

  const uploadModel = async (formData, onProgress) => {
    try {
      const response = await modelsApi.upload(formData, onProgress)
      return response.data
    } catch (error) {
      console.error('Failed to upload model:', error)
      throw error
    }
  }

  const createModelFromUrl = async (formData, onProgress) => {
    try {
      const response = await modelsApi.createFromUrl(formData, onProgress)
      return response.data
    } catch (error) {
      console.error('Failed to create model from URL:', error)
      throw error
    }
  }

  const updateModel = async (id, data) => {
    try {
      const response = await modelsApi.update(id, data)
      return response.data
    } catch (error) {
      console.error('Failed to update model:', error)
      throw error
    }
  }

  const deleteModel = async (id) => {
    try {
      await modelsApi.delete(id)
      models.value = models.value.filter(m => m.id !== id)
    } catch (error) {
      console.error('Failed to delete model:', error)
      throw error
    }
  }

  const buildModel = async (id, data) => {
    try {
      const response = await modelsApi.build(id, data)
      return response.data
    } catch (error) {
      console.error('Failed to build model:', error)
      throw error
    }
  }

  const stopBuild = async (id) => {
    try {
      const response = await modelsApi.stopBuild(id)
      return response.data
    } catch (error) {
      console.error('Failed to stop build:', error)
      throw error
    }
  }

  const resetStatus = async (id) => {
    try {
      const response = await modelsApi.resetStatus(id)
      return response.data
    } catch (error) {
      console.error('Failed to reset status:', error)
      throw error
    }
  }

  const getModelStatus = async (id) => {
    try {
      const response = await modelsApi.getStatus(id)
      return response.data
    } catch (error) {
      console.error('Failed to get model status:', error)
      throw error
    }
  }

  const fetchActiveBuildModels = async () => {
    const activeModels = []
    for (const status of ['building', 'pushing']) {
      const response = await modelsApi.getList({ status, limit: 100 })
      activeModels.push(...response.data.items)
    }
    return activeModels
  }

  return {
    models,
    currentModel,
    loading,
    total,
    modelList,
    isLoading,
    fetchModels,
    fetchModelDetail,
    createModel,
    uploadModel,
    createModelFromUrl,
    updateModel,
    deleteModel,
    buildModel,
    stopBuild,
    resetStatus,
    getModelStatus,
    fetchActiveBuildModels
  }
})
