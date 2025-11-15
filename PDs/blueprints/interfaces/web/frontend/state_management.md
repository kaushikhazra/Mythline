# Frontend: State Management

Managing component state with React hooks.

---

## Overview

**Use when:** Managing form data, tracking UI state, handling async operations, component lifecycle.

**Pattern:**
```
Initialize State → Update via Handlers → Trigger Re-renders → Side Effects
```

---

## useState Hook

### Basic Usage

```javascript
import { useState } from 'react'

function MyComponent() {
  const [value, setValue] = useState(initialValue)

  return (
    <div>
      <p>Value: {value}</p>
      <button onClick={() => setValue('new value')}>Update</button>
    </div>
  )
}
```

### State Types

```javascript
// String state
const [name, setName] = useState('')

// Number state
const [count, setCount] = useState(0)

// Boolean state
const [isActive, setIsActive] = useState(false)

// Array state
const [items, setItems] = useState([])

// Object state
const [user, setUser] = useState({ name: '', email: '' })

// Null state
const [data, setData] = useState(null)
```

---

## Updating State

### Simple Updates

```javascript
// Direct value
setValue('new value')

// Increment number
setCount(count + 1)

// Toggle boolean
setIsActive(!isActive)
```

### Functional Updates

**Use when:** Update depends on previous state.

```javascript
// Correct - functional update
setCount(prevCount => prevCount + 1)

// Wrong - may have stale value
setCount(count + 1)
```

**Why functional updates?**
```javascript
// This may not work as expected
const increment = () => {
  setCount(count + 1)
  setCount(count + 1) // Uses same count value
  // Result: count + 1, not count + 2
}

// This works correctly
const increment = () => {
  setCount(prev => prev + 1)
  setCount(prev => prev + 1)
  // Result: count + 2
}
```

---

## Object State

### Updating Object Properties

```javascript
const [user, setUser] = useState({
  name: '',
  email: '',
  age: 0
})

// Update single property
const updateName = (newName) => {
  setUser(prevUser => ({
    ...prevUser,
    name: newName
  }))
}

// Update multiple properties
const updateUser = (name, email) => {
  setUser(prevUser => ({
    ...prevUser,
    name: name,
    email: email
  }))
}
```

### Nested Object Updates

```javascript
const [data, setData] = useState({
  user: {
    name: '',
    settings: {
      theme: 'light'
    }
  }
})

// Update nested property
const updateTheme = (newTheme) => {
  setData(prevData => ({
    ...prevData,
    user: {
      ...prevData.user,
      settings: {
        ...prevData.user.settings,
        theme: newTheme
      }
    }
  }))
}
```

---

## Array State

### Adding Items

```javascript
const [items, setItems] = useState([])

// Add to end
setItems(prevItems => [...prevItems, newItem])

// Add to beginning
setItems(prevItems => [newItem, ...prevItems])

// Add at index
setItems(prevItems => [
  ...prevItems.slice(0, index),
  newItem,
  ...prevItems.slice(index)
])
```

### Updating Items

```javascript
// Update item by index
setItems(prevItems =>
  prevItems.map((item, idx) =>
    idx === index ? updatedItem : item
  )
)

// Update item by ID
setItems(prevItems =>
  prevItems.map(item =>
    item.id === targetId ? { ...item, ...updates } : item
  )
)
```

### Removing Items

```javascript
// Remove by index
setItems(prevItems =>
  prevItems.filter((_, idx) => idx !== index)
)

// Remove by ID
setItems(prevItems =>
  prevItems.filter(item => item.id !== targetId)
)

// Remove by condition
setItems(prevItems =>
  prevItems.filter(item => item.status !== 'deleted')
)
```

### Sorting and Filtering

```javascript
// Sort items
setItems(prevItems =>
  [...prevItems].sort((a, b) => a.name.localeCompare(b.name))
)

// Filter items
const filterActive = () => {
  setFilteredItems(items.filter(item => item.active))
}
```

---

## useEffect Hook

### Basic Usage

```javascript
import { useEffect } from 'react'

function MyComponent() {
  const [data, setData] = useState(null)

  useEffect(() => {
    // Side effect code
    fetchData()
  }, []) // Dependency array

  return <div>{data}</div>
}
```

### Dependency Array Patterns

```javascript
// Run once on mount
useEffect(() => {
  console.log('Component mounted')
}, [])

// Run on every render (rarely needed)
useEffect(() => {
  console.log('Component rendered')
})

// Run when dependencies change
useEffect(() => {
  console.log('Count changed:', count)
}, [count])

// Run when any dependency changes
useEffect(() => {
  console.log('Count or name changed')
}, [count, name])
```

### Cleanup Functions

```javascript
useEffect(() => {
  // Setup
  const interval = setInterval(() => {
    console.log('Tick')
  }, 1000)

  // Cleanup
  return () => {
    clearInterval(interval)
  }
}, [])
```

**Common cleanup scenarios:**
```javascript
// Event listeners
useEffect(() => {
  const handleClick = () => console.log('Clicked')
  window.addEventListener('click', handleClick)

  return () => {
    window.removeEventListener('click', handleClick)
  }
}, [])

// Timers
useEffect(() => {
  const timer = setTimeout(() => {
    doSomething()
  }, 1000)

  return () => clearTimeout(timer)
}, [])

// Subscriptions
useEffect(() => {
  const subscription = subscribe(data)

  return () => subscription.unsubscribe()
}, [])
```

---

## Common State Patterns

### Loading State

```javascript
const [isLoading, setIsLoading] = useState(false)

const fetchData = async () => {
  setIsLoading(true)
  try {
    const data = await api.getData()
    setData(data)
  } finally {
    setIsLoading(false)
  }
}

// Render
{isLoading ? <Spinner /> : <Content />}
```

### Error State

```javascript
const [error, setError] = useState(null)

const handleAction = async () => {
  setError(null)
  try {
    await riskyOperation()
  } catch (err) {
    setError(err.message)
  }
}

// Render
{error && <ErrorMessage message={error} />}
```

### Form State

```javascript
const [formData, setFormData] = useState({
  username: '',
  email: '',
  password: ''
})

const handleChange = (event) => {
  const { name, value } = event.target
  setFormData(prev => ({
    ...prev,
    [name]: value
  }))
}

const handleSubmit = (event) => {
  event.preventDefault()
  submitForm(formData)
}

// Render
<input
  name="username"
  value={formData.username}
  onChange={handleChange}
/>
```

### Toggle State

```javascript
const [isOpen, setIsOpen] = useState(false)

const toggle = () => setIsOpen(prev => !prev)

// Render
<button onClick={toggle}>
  {isOpen ? 'Close' : 'Open'}
</button>
```

### Multi-Select State

```javascript
const [selectedItems, setSelectedItems] = useState([])

const toggleItem = (itemId) => {
  setSelectedItems(prev =>
    prev.includes(itemId)
      ? prev.filter(id => id !== itemId)
      : [...prev, itemId]
  )
}

const isSelected = (itemId) => selectedItems.includes(itemId)

// Render
<checkbox
  checked={isSelected(item.id)}
  onChange={() => toggleItem(item.id)}
/>
```

---

## Derived State

**Compute values from existing state instead of storing separately.**

```javascript
const [items, setItems] = useState([])

// Derived values (no separate state needed)
const itemCount = items.length
const hasItems = items.length > 0
const activeItems = items.filter(item => item.active)
const totalPrice = items.reduce((sum, item) => sum + item.price, 0)

// Render
<p>Total items: {itemCount}</p>
<p>Active items: {activeItems.length}</p>
<p>Total price: ${totalPrice}</p>
```

---

## Lazy Initialization

**Use when initial state is expensive to compute.**

```javascript
// Wrong - computes on every render
const [data, setData] = useState(expensiveComputation())

// Correct - computes only once
const [data, setData] = useState(() => expensiveComputation())
```

**Example:**
```javascript
const [sessions, setSessions] = useState(() => {
  const saved = localStorage.getItem('sessions')
  return saved ? JSON.parse(saved) : []
})
```

---

## Multiple Related States

### Group Related State

```javascript
// Instead of this
const [username, setUsername] = useState('')
const [email, setEmail] = useState('')
const [age, setAge] = useState(0)

// Consider this
const [user, setUser] = useState({
  username: '',
  email: '',
  age: 0
})
```

### Separate Independent State

```javascript
// Good - independent concerns
const [userData, setUserData] = useState({})
const [isLoading, setIsLoading] = useState(false)
const [error, setError] = useState(null)
```

---

## useEffect Patterns

### Fetch Data on Mount

```javascript
useEffect(() => {
  const fetchData = async () => {
    const response = await fetch(url)
    const data = await response.json()
    setData(data)
  }

  fetchData()
}, [])
```

### Fetch Data When Dependency Changes

```javascript
useEffect(() => {
  if (!userId) return

  const fetchUser = async () => {
    const response = await fetch(`/api/users/${userId}`)
    const user = await response.json()
    setUser(user)
  }

  fetchUser()
}, [userId])
```

### Polling/Interval

```javascript
useEffect(() => {
  const interval = setInterval(() => {
    checkStatus()
  }, 2000)

  return () => clearInterval(interval)
}, [])
```

### Sync State with localStorage

```javascript
useEffect(() => {
  localStorage.setItem('theme', theme)
}, [theme])

// Initialize from localStorage
const [theme, setTheme] = useState(() => {
  return localStorage.getItem('theme') || 'light'
})
```

---

## Complete Example

### Research Page State Management

```javascript
import { useState, useEffect } from 'react'

function Research() {
  // Data state
  const [sessions, setSessions] = useState([])
  const [selectedSession, setSelectedSession] = useState('')
  const [messages, setMessages] = useState([])
  const [query, setQuery] = useState('')

  // UI state
  const [isLoadingSessions, setIsLoadingSessions] = useState(true)
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Load sessions on mount
  useEffect(() => {
    const loadSessions = async () => {
      setIsLoadingSessions(true)
      setError(null)

      try {
        const response = await fetch('http://localhost:8080/api/sessions')
        const data = await response.json()

        setSessions(data.sessions)

        if (data.sessions.length > 0) {
          setSelectedSession(data.sessions[0])
        }
      } catch (err) {
        setError('Failed to load sessions')
      } finally {
        setIsLoadingSessions(false)
      }
    }

    loadSessions()
  }, [])

  // Load messages when session changes
  useEffect(() => {
    if (!selectedSession) return

    const loadMessages = async () => {
      setIsLoadingMessages(true)
      setError(null)

      try {
        const response = await fetch(
          `http://localhost:8080/api/messages/${selectedSession}`
        )
        const data = await response.json()
        setMessages(data.messages)
      } catch (err) {
        setError('Failed to load messages')
      } finally {
        setIsLoadingMessages(false)
      }
    }

    loadMessages()
  }, [selectedSession])

  // Event handlers
  const handleSessionChange = (event) => {
    setSelectedSession(event.target.value)
  }

  const handleQueryChange = (event) => {
    setQuery(event.target.value)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!query.trim()) return

    setIsSubmitting(true)
    setError(null)

    try {
      const response = await fetch('http://localhost:8080/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: query,
          session_id: selectedSession
        })
      })

      const data = await response.json()

      // Add messages to state
      setMessages(prev => [
        ...prev,
        { role: 'user', content: query },
        { role: 'assistant', content: data.output }
      ])

      // Clear input
      setQuery('')
    } catch (err) {
      setError('Failed to submit query')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Derived state
  const hasMessages = messages.length > 0
  const canSubmit = query.trim() && !isSubmitting

  return (
    <div>
      {/* Session selector */}
      {isLoadingSessions ? (
        <p>Loading sessions...</p>
      ) : (
        <select value={selectedSession} onChange={handleSessionChange}>
          {sessions.map(session => (
            <option key={session} value={session}>
              {session}
            </option>
          ))}
        </select>
      )}

      {/* Error display */}
      {error && <div className="error">{error}</div>}

      {/* Messages */}
      {isLoadingMessages ? (
        <p>Loading messages...</p>
      ) : hasMessages ? (
        <div className="messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={msg.role}>
              {msg.content}
            </div>
          ))}
        </div>
      ) : (
        <p>No messages yet</p>
      )}

      {/* Query form */}
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={query}
          onChange={handleQueryChange}
          placeholder="Enter query..."
          disabled={isSubmitting}
        />
        <button type="submit" disabled={!canSubmit}>
          {isSubmitting ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  )
}

export default Research
```

---

## Best Practices

**DO:**
- Use functional updates when new state depends on previous state
- Group related state together
- Use derived state instead of duplicating state
- Initialize expensive state lazily
- Clean up effects properly
- Use descriptive state names

**DON'T:**
- Mutate state directly
- Use state for values that can be computed
- Forget dependencies in useEffect
- Call hooks conditionally
- Store props in state (use props directly)
- Over-use useEffect

---

## Related Documentation

- `page_component.md` - Component structure
- `api_communication.md` - API integration with state
- `form_handling.md` - Form state patterns
- `../COMMON.md` - Common patterns
