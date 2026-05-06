import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useBuildStore = defineStore('build', () => {
  const building = ref(false)
  const buildProgress = ref(0)
  const buildError = ref('')
  const currentTaskId = ref('')
  const currentModelId = ref(null)
  const progressMessage = ref('')
  const isProgressMinimized = ref(false)
  const progressDialogVisible = ref(false)

  const isBuilding = computed(() => building.value)
  const isMinimized = computed(() => isProgressMinimized.value)

  const startBuild = (taskId, modelId) => {
    building.value = true
    buildProgress.value = 0
    buildError.value = ''
    currentTaskId.value = taskId
    currentModelId.value = modelId
    progressMessage.value = '构建开始...'
    isProgressMinimized.value = false
    progressDialogVisible.value = true
  }

  const updateProgress = (progress, message) => {
    buildProgress.value = progress
    if (message) {
      progressMessage.value = message
    }
  }

  const setError = (error) => {
    buildError.value = error
    building.value = false
    isProgressMinimized.value = false
  }

  const completeBuild = () => {
    building.value = false
    buildProgress.value = 100
    isProgressMinimized.value = false
  }

  const minimizeProgress = () => {
    isProgressMinimized.value = true
    progressDialogVisible.value = false
  }

  const restoreProgress = () => {
    isProgressMinimized.value = false
    progressDialogVisible.value = true
  }

  const closeProgress = () => {
    progressDialogVisible.value = false
    if (!building.value) {
      resetBuild()
    }
  }

  const resetBuild = () => {
    building.value = false
    buildProgress.value = 0
    buildError.value = ''
    currentTaskId.value = ''
    currentModelId.value = null
    progressMessage.value = ''
    isProgressMinimized.value = false
    progressDialogVisible.value = false
  }

  const stopBuild = () => {
    building.value = false
    buildError.value = '构建已停止'
    isProgressMinimized.value = false
  }

  return {
    building,
    buildProgress,
    buildError,
    currentTaskId,
    currentModelId,
    progressMessage,
    isProgressMinimized,
    progressDialogVisible,
    isBuilding,
    isMinimized,
    startBuild,
    updateProgress,
    setError,
    completeBuild,
    minimizeProgress,
    restoreProgress,
    closeProgress,
    resetBuild,
    stopBuild
  }
})
