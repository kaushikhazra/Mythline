# Frontend: API Communication

Making API calls from React components using the Fetch API.

---

## Overview

**Use when:** Fetching data from backend, submitting forms, polling for updates, file uploads/downloads.

**Pattern:**
```
Define API Function → Call in useEffect/Handler → Update State → Handle Errors
```

---

## Basic API Calls

### GET Request

```javascript
const fetchData = async () => {
  setIsLoading(true)
  setError(null)

  try {
    const response = await fetch(`${API_BASE_URL}/api/endpoint`)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    setData(data)
  } catch (err) {
    setError(err.message)
  } finally {
    setIsLoading(false)
  }
}
```

### POST Request

```javascript
const submitData = async (payload) => {
  setIsLoading(true)
  setError(null)

  try {
    const response = await fetch(`${API_BASE_URL}/api/endpoint`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    return data
  } catch (err) {
    setError(err.message)
    throw err
  } finally {
    setIsLoading(false)
  }
}
```

### PUT Request

```javascript
const updateData = async (id, payload) => {
  const response = await fetch(`${API_BASE_URL}/api/endpoint/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  return await response.json()
}
```

### DELETE Request

```javascript
const deleteData = async (id) => {
  const response = await fetch(`${API_BASE_URL}/api/endpoint/${id}`, {
    method: 'DELETE'
  })

  return await response.json()
}
```

---

## API Call Patterns

### Pattern 1: Call in useEffect

**Use when:** Loading data on component mount or when dependencies change.

```javascript
function MyComponent() {
  const [data, setData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/data`)
        const result = await response.json()
        setData(result)
      } catch (err) {
        setError(err.message)
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, []) // Empty array = run once on mount

  return (
    <div>
      {isLoading && <p>Loading...</p>}
      {error && <p>Error: {error}</p>}
      {data && <p>Data: {JSON.stringify(data)}</p>}
    </div>
  )
}
```

### Pattern 2: Call in Event Handler

**Use when:** Submitting forms, button clicks, user interactions.

```javascript
function MyComponent() {
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE_URL}/api/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: 'value' })
      })

      const data = await response.json()
      setResult(data)
    } catch (err) {
      console.error('Error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Submitting...' : 'Submit'}
      </button>
    </form>
  )
}
```

### Pattern 3: Dependent Data Loading

**Use when:** Loading data based on another state value.

```javascript
function MyComponent() {
  const [userId, setUserId] = useState(null)
  const [userDetails, setUserDetails] = useState(null)

  // Load user details when userId changes
  useEffect(() => {
    if (!userId) return

    const fetchUserDetails = async () => {
      const response = await fetch(`${API_BASE_URL}/api/users/${userId}`)
      const data = await response.json()
      setUserDetails(data)
    }

    fetchUserDetails()
  }, [userId]) // Re-run when userId changes

  return <div>{/* UI */}</div>
}
```

---

## Error Handling

### Basic Error Handling

```javascript
try {
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const data = await response.json()
} catch (err) {
  console.error('Fetch error:', err)
  setError(err.message)
}
```

### Detailed Error Handling

```javascript
const fetchData = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/data`)

    if (!response.ok) {
      // Try to parse error message from backend
      try {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      } catch {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
    }

    const data = await response.json()
    setData(data)
  } catch (err) {
    if (err.name === 'TypeError') {
      setError('Network error. Please check your connection.')
    } else {
      setError(err.message)
    }
  }
}
```

### Error Display

```javascript
{error && (
  <div className="error-message">
    <p>Error: {error}</p>
    <button onClick={() => setError(null)}>Dismiss</button>
  </div>
)}
```

---

## Response Handling

### JSON Response

```javascript
const response = await fetch(url)
const data = await response.json()
```

### Text Response

```javascript
const response = await fetch(url)
const text = await response.text()
```

### Blob Response (File Download)

```javascript
const response = await fetch(url)
const blob = await response.blob()
const downloadUrl = window.URL.createObjectURL(blob)

// Trigger download
const link = document.createElement('a')
link.href = downloadUrl
link.download = 'filename.txt'
link.click()
```

### Status Code Checking

```javascript
const response = await fetch(url)

if (response.status === 200) {
  // OK
} else if (response.status === 404) {
  // Not found
} else if (response.status === 500) {
  // Server error
}
```

---

## Loading States

### Simple Loading State

```javascript
const [isLoading, setIsLoading] = useState(false)

const fetchData = async () => {
  setIsLoading(true)
  try {
    // API call
  } finally {
    setIsLoading(false)
  }
}

// Render
{isLoading ? <p>Loading...</p> : <Content />}
```

### Multiple Loading States

```javascript
const [loadingStates, setLoadingStates] = useState({
  sessions: false,
  messages: false,
  submission: false
})

const setLoading = (key, value) => {
  setLoadingStates(prev => ({ ...prev, [key]: value }))
}

// Usage
setLoading('sessions', true)
// API call
setLoading('sessions', false)

// Render
{loadingStates.sessions && <p>Loading sessions...</p>}
```

---

## File Upload

### Single File Upload

```javascript
const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData // Don't set Content-Type header
    })

    const data = await response.json()
    console.log('Upload success:', data)
  } catch (err) {
    console.error('Upload error:', err)
  }
}

// Render
<input type="file" onChange={handleFileUpload} />
```

### Multiple File Upload

```javascript
const handleMultipleUpload = async (event) => {
  const files = Array.from(event.target.files)

  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file)
  })

  const response = await fetch(`${API_BASE_URL}/api/upload-multiple`, {
    method: 'POST',
    body: formData
  })
}

// Render
<input type="file" multiple onChange={handleMultipleUpload} />
```

---

## File Download

### Trigger File Download

```javascript
const downloadFile = async (filename) => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/download/${filename}`
    )

    if (!response.ok) throw new Error('Download failed')

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Download error:', err)
  }
}

// Usage
<button onClick={() => downloadFile('story.md')}>Download</button>
```

---

## Polling Pattern

### Basic Polling

```javascript
function PollingComponent() {
  const [taskId, setTaskId] = useState(null)
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)

  // Poll for status
  useEffect(() => {
    if (!taskId) return

    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/status/${taskId}`
        )
        const data = await response.json()

        setStatus(data.status)

        if (data.status === 'completed') {
          setResult(data.result)
          clearInterval(interval)
        } else if (data.status === 'error') {
          setError(data.error)
          clearInterval(interval)
        }
      } catch (err) {
        setError(err.message)
        clearInterval(interval)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [taskId])

  return (
    <div>
      <p>Status: {status}</p>
      {result && <p>Result: {result}</p>}
    </div>
  )
}
```

### Polling with Progress

```javascript
useEffect(() => {
  if (!taskId) return

  const interval = setInterval(async () => {
    const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`)
    const data = await response.json()

    setProgress(data.progress) // 0-100
    setStatus(data.status)

    if (data.status === 'completed') {
      setResult(data.result)
      clearInterval(interval)
    }
  }, 1000)

  return () => clearInterval(interval)
}, [taskId])

// Render
<progress value={progress} max="100">{progress}%</progress>
```

---

## Request Cancellation

### Using AbortController

```javascript
function MyComponent() {
  const [data, setData] = useState(null)

  useEffect(() => {
    const abortController = new AbortController()

    const fetchData = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/data`, {
          signal: abortController.signal
        })
        const data = await response.json()
        setData(data)
      } catch (err) {
        if (err.name === 'AbortError') {
          console.log('Fetch aborted')
        } else {
          console.error('Fetch error:', err)
        }
      }
    }

    fetchData()

    return () => {
      abortController.abort() // Cancel request on unmount
    }
  }, [])

  return <div>{/* UI */}</div>
}
```

---

## API Utilities

### Reusable API Function

```javascript
// api.js
export const apiCall = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return await response.json()
}

// Usage in component
import { apiCall } from './api'

const data = await apiCall('/api/data')

const result = await apiCall('/api/submit', {
  method: 'POST',
  body: JSON.stringify({ key: 'value' })
})
```

---

## Complete Example

### Story Generator with Polling

```javascript
import { useState, useEffect } from 'react'

function StoryGenerator() {
  const API_BASE_URL = 'http://localhost:8080'

  const [subject, setSubject] = useState('')
  const [taskId, setTaskId] = useState(null)
  const [status, setStatus] = useState(null)
  const [story, setStory] = useState(null)
  const [error, setError] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  // Start generation
  const startGeneration = async () => {
    setIsLoading(true)
    setError(null)
    setTaskId(null)
    setStatus(null)
    setStory(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/story/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: subject,
          session_id: `session_${Date.now()}`
        })
      })

      if (!response.ok) throw new Error('Failed to start generation')

      const data = await response.json()
      setTaskId(data.task_id)
      setStatus('started')
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  // Poll for status
  useEffect(() => {
    if (!taskId) return

    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/story/status/${taskId}`
        )
        const data = await response.json()

        setStatus(data.status)

        if (data.status === 'completed') {
          setStory(data.result)
          clearInterval(interval)
        } else if (data.status === 'error') {
          setError(data.error)
          clearInterval(interval)
        }
      } catch (err) {
        setError('Failed to check status')
        clearInterval(interval)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [taskId])

  const handleSubmit = (event) => {
    event.preventDefault()
    startGeneration()
  }

  return (
    <div className="story-generator">
      <h1>Story Generator</h1>

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="Enter story subject..."
          disabled={isLoading || status === 'running'}
        />
        <button
          type="submit"
          disabled={!subject || isLoading || status === 'running'}
        >
          Generate Story
        </button>
      </form>

      {error && <div className="error">Error: {error}</div>}

      {status && (
        <div className="status">
          Status: {status}
          {status === 'running' && ' (This may take a few minutes...)'}
        </div>
      )}

      {story && (
        <div className="story">
          <h2>Generated Story</h2>
          <pre>{story}</pre>
        </div>
      )}
    </div>
  )
}

export default StoryGenerator
```

---

## Best Practices

**DO:**
- Always handle errors
- Show loading states
- Clean up in useEffect
- Use AbortController for cancellable requests
- Validate responses
- Set appropriate timeouts

**DON'T:**
- Forget error handling
- Make API calls without loading states
- Ignore response status codes
- Hardcode API URLs
- Forget to clean up intervals
- Call APIs in render functions

---

## Related Documentation

- `page_component.md` - Component structure
- `state_management.md` - Managing state
- `../integration/polling_pattern.md` - Polling implementation
- `../COMMON.md` - Common patterns
