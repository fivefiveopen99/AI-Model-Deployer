import { ref, onMounted, onUnmounted } from 'vue'

export function useWebSocket() {
  const ws = ref(null)
  const isConnected = ref(false)
  const progress = ref(0)
  const progressMessage = ref('')
  const error = ref(null)
  const pendingSubscriptions = new Set()
  let reconnectTimer = null
  let manuallyClosed = false

  const connect = () => {
    manuallyClosed = false
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/progress`
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      isConnected.value = true
      error.value = null
      console.log('WebSocket connected')
      pendingSubscriptions.forEach((taskId) => {
        sendSubscribe(taskId)
      })
    }

    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'progress') {
        progress.value = data.progress
        progressMessage.value = data.message
      } else if (data.type === 'error') {
        error.value = data.message
      }
    }

    ws.value.onerror = (err) => {
      console.warn('WebSocket error:', err)
    }

    ws.value.onclose = () => {
      isConnected.value = false
      console.log('WebSocket disconnected')
      if (!manuallyClosed) {
        clearTimeout(reconnectTimer)
        reconnectTimer = setTimeout(connect, 2000)
      }
    }
  }

  const sendSubscribe = (taskId) => {
    ws.value.send(JSON.stringify({
      action: 'subscribe',
      task_id: taskId
    }))
  }

  const subscribe = (taskId) => {
    if (ws.value && isConnected.value) {
      sendSubscribe(taskId)
    } else {
      pendingSubscriptions.add(taskId)
    }
  }

  const unsubscribe = (taskId) => {
    if (ws.value && isConnected.value) {
      ws.value.send(JSON.stringify({
        action: 'unsubscribe',
        task_id: taskId
      }))
    }
    pendingSubscriptions.delete(taskId)
  }

  const disconnect = () => {
    manuallyClosed = true
    clearTimeout(reconnectTimer)
    if (ws.value) {
      ws.value.close()
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    progress,
    progressMessage,
    error,
    connect,
    subscribe,
    unsubscribe,
    disconnect
  }
}
