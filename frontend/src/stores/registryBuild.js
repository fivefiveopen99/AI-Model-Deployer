import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const REGISTRY_BUILD_STATE_KEY = 'ai-model-deployer-registry-build-state'

export const useRegistryBuildStore = defineStore('registryBuild', () => {
  const building = ref(false)
  const buildProgress = ref(0)
  const buildError = ref('')
  const currentTaskId = ref('')
  const progressMessage = ref('')
  const isProgressMinimized = ref(false)
  const progressDialogVisible = ref(false)
  const buildLogs = ref([])
  const resultImage = ref('')

  const isBuilding = computed(() => building.value)
  const isMinimized = computed(() => isProgressMinimized.value)

  const persistState = () => {
    localStorage.setItem(REGISTRY_BUILD_STATE_KEY, JSON.stringify({
      building: building.value,
      buildProgress: buildProgress.value,
      buildError: buildError.value,
      currentTaskId: currentTaskId.value,
      progressMessage: progressMessage.value,
      isProgressMinimized: isProgressMinimized.value,
      progressDialogVisible: progressDialogVisible.value,
      buildLogs: buildLogs.value.slice(-1000),
      resultImage: resultImage.value
    }))
  }

  const restorePersistedState = () => {
    const raw = localStorage.getItem(REGISTRY_BUILD_STATE_KEY)
    if (!raw) return null
    try {
      const state = JSON.parse(raw)
      building.value = Boolean(state.building)
      buildProgress.value = Number(state.buildProgress || 0)
      buildError.value = state.buildError || ''
      currentTaskId.value = state.currentTaskId || ''
      progressMessage.value = state.progressMessage || ''
      isProgressMinimized.value = Boolean(state.isProgressMinimized)
      progressDialogVisible.value = Boolean(state.progressDialogVisible && state.building)
      buildLogs.value = Array.isArray(state.buildLogs) ? state.buildLogs.slice(-1000) : []
      resultImage.value = state.resultImage || ''
      return state
    } catch {
      localStorage.removeItem(REGISTRY_BUILD_STATE_KEY)
      return null
    }
  }

  const clearPersistedState = () => {
    localStorage.removeItem(REGISTRY_BUILD_STATE_KEY)
  }

  const startBuild = (taskId = '') => {
    building.value = true
    buildProgress.value = 0
    buildError.value = ''
    currentTaskId.value = taskId
    progressMessage.value = '构建开始...'
    isProgressMinimized.value = false
    progressDialogVisible.value = true
    buildLogs.value = ['构建开始...']
    resultImage.value = ''
    persistState()
  }

  const setTask = (taskId) => {
    currentTaskId.value = taskId
    persistState()
  }

  const resumeBuild = ({ taskId, progress = 0, message = '构建任务恢复中...', minimized = true }) => {
    building.value = true
    currentTaskId.value = taskId
    buildProgress.value = progress
    progressMessage.value = message
    isProgressMinimized.value = minimized
    progressDialogVisible.value = !minimized
    persistState()
  }

  const updateProgress = (progress, message) => {
    buildProgress.value = progress
    if (message) {
      progressMessage.value = message
    }
    persistState()
  }

  const addLog = (line) => {
    if (!line) return
    buildLogs.value.push(line)
    if (buildLogs.value.length > 1000) {
      buildLogs.value.splice(0, buildLogs.value.length - 1000)
    }
    persistState()
  }

  const setLogs = (logs) => {
    buildLogs.value = Array.isArray(logs) ? logs.slice(-1000) : []
    persistState()
  }

  const setError = (message) => {
    buildError.value = message
    building.value = false
    isProgressMinimized.value = false
    progressDialogVisible.value = true
    persistState()
  }

  const completeBuild = (image = '') => {
    building.value = false
    buildProgress.value = 100
    isProgressMinimized.value = false
    progressDialogVisible.value = true
    resultImage.value = image || resultImage.value
    persistState()
  }

  const minimizeProgress = () => {
    isProgressMinimized.value = true
    progressDialogVisible.value = false
    persistState()
  }

  const restoreProgress = () => {
    isProgressMinimized.value = false
    progressDialogVisible.value = true
    persistState()
  }

  const closeProgress = () => {
    progressDialogVisible.value = false
    if (!building.value) {
      resetBuild()
    } else {
      persistState()
    }
  }

  const resetBuild = () => {
    building.value = false
    buildProgress.value = 0
    buildError.value = ''
    currentTaskId.value = ''
    progressMessage.value = ''
    isProgressMinimized.value = false
    progressDialogVisible.value = false
    buildLogs.value = []
    resultImage.value = ''
    clearPersistedState()
  }

  const stopBuild = () => {
    building.value = false
    buildError.value = '构建已停止'
    isProgressMinimized.value = false
    progressDialogVisible.value = true
    persistState()
  }

  return {
    building,
    buildProgress,
    buildError,
    currentTaskId,
    progressMessage,
    isProgressMinimized,
    progressDialogVisible,
    buildLogs,
    resultImage,
    isBuilding,
    isMinimized,
    restorePersistedState,
    startBuild,
    setTask,
    resumeBuild,
    updateProgress,
    addLog,
    setLogs,
    setError,
    completeBuild,
    minimizeProgress,
    restoreProgress,
    closeProgress,
    resetBuild,
    stopBuild
  }
})
