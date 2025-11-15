# Frontend: Page Component

React page component structure and organization.

---

## Overview

**Use when:** Creating new pages, building reusable components, structuring UI logic.

**Pattern:**
```
Component Definition → State Setup → API Integration → Event Handlers → Render UI
```

---

## Component Structure

### Basic Page Component

```javascript
import { useState, useEffect } from 'react'

function MyPage() {
  // State declarations
  const [data, setData] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // API calls and side effects
  useEffect(() => {
    fetchInitialData()
  }, [])

  const fetchInitialData = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('http://localhost:8080/api/data')
      const result = await response.json()
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  // Event handlers
  const handleAction = async () => {
    // Handle user action
  }

  // Render
  return (
    <div className="my-page">
      <h1>My Page</h1>

      {isLoading && <p>Loading...</p>}
      {error && <div className="error">{error}</div>}
      {data && <div>{/* Display data */}</div>}
    </div>
  )
}

export default MyPage
```

---

## Component Organization

### Section 1: Imports

```javascript
// React imports
import { useState, useEffect, useCallback } from 'react'

// Router imports
import { useNavigate, useParams } from 'react-router-dom'

// Component imports
import Header from '../components/Header'

// Styles
import './MyPage.css'
```

### Section 2: State Declarations

```javascript
function MyPage() {
  // UI state
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Data state
  const [items, setItems] = useState([])
  const [selectedItem, setSelectedItem] = useState(null)

  // Form state
  const [formData, setFormData] = useState({
    field1: '',
    field2: ''
  })
```

### Section 3: Side Effects

```javascript
  // Initial data fetch
  useEffect(() => {
    loadInitialData()
  }, [])

  // Dependent data fetch
  useEffect(() => {
    if (selectedItem) {
      loadItemDetails(selectedItem)
    }
  }, [selectedItem])
```

### Section 4: API Functions

```javascript
  const loadInitialData = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/items`)
      if (!response.ok) throw new Error('Failed to load')
      const data = await response.json()
      setItems(data.items)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }
```

### Section 5: Event Handlers

```javascript
  const handleSelect = (item) => {
    setSelectedItem(item)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    // Submit logic
  }

  const handleInputChange = (event) => {
    const { name, value } = event.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }
```

### Section 6: Render

```javascript
  return (
    <div className="my-page">
      <Header title="My Page" />

      {error && <ErrorMessage message={error} />}

      {isLoading ? (
        <Loading />
      ) : (
        <Content data={items} onSelect={handleSelect} />
      )}

      <Form
        data={formData}
        onChange={handleInputChange}
        onSubmit={handleSubmit}
      />
    </div>
  )
}

export default MyPage
```

---

## State Patterns

### Loading State

```javascript
const [isLoading, setIsLoading] = useState(false)

// Usage
const fetchData = async () => {
  setIsLoading(true)
  try {
    // Fetch data
  } finally {
    setIsLoading(false)
  }
}

// Render
{isLoading && <p>Loading...</p>}
```

### Error State

```javascript
const [error, setError] = useState(null)

// Usage
try {
  // Operation
} catch (err) {
  setError(err.message)
}

// Render
{error && <div className="error">{error}</div>}
```

### Data State

```javascript
const [data, setData] = useState(null)

// Array state
const [items, setItems] = useState([])

// Object state
const [user, setUser] = useState({ name: '', email: '' })
```

### Form State

```javascript
const [formData, setFormData] = useState({
  field1: '',
  field2: '',
  field3: false
})

const handleChange = (event) => {
  const { name, value, type, checked } = event.target
  setFormData(prev => ({
    ...prev,
    [name]: type === 'checkbox' ? checked : value
  }))
}
```

---

## Conditional Rendering

### Loading/Error/Data Pattern

```javascript
return (
  <div>
    {isLoading && <p>Loading...</p>}

    {error && <div className="error">{error}</div>}

    {!isLoading && !error && data && (
      <div>{/* Display data */}</div>
    )}

    {!isLoading && !error && !data && (
      <p>No data available</p>
    )}
  </div>
)
```

### Ternary Operator

```javascript
{isLoading ? (
  <Loading />
) : (
  <Content data={data} />
)}
```

### Logical AND

```javascript
{items.length > 0 && (
  <ul>
    {items.map(item => <li key={item.id}>{item.name}</li>)}
  </ul>
)}
```

---

## Props Pattern

### Receiving Props

```javascript
function MyComponent({ title, data, onAction }) {
  return (
    <div>
      <h2>{title}</h2>
      <button onClick={onAction}>Action</button>
    </div>
  )
}
```

### Default Props

```javascript
function MyComponent({ title = 'Default Title', items = [] }) {
  return <div>{title}: {items.length}</div>
}
```

### Destructuring Props

```javascript
function UserCard({ user: { name, email, avatar } }) {
  return (
    <div>
      <img src={avatar} alt={name} />
      <h3>{name}</h3>
      <p>{email}</p>
    </div>
  )
}
```

---

## Event Handling

### Form Events

```javascript
const handleSubmit = async (event) => {
  event.preventDefault()

  const formData = new FormData(event.target)
  const data = Object.fromEntries(formData)

  await submitData(data)
}

const handleChange = (event) => {
  const { name, value } = event.target
  setFormData(prev => ({ ...prev, [name]: value }))
}
```

### Click Events

```javascript
const handleClick = () => {
  console.log('Clicked')
}

const handleItemClick = (item) => {
  setSelectedItem(item)
}

// Render
<button onClick={handleClick}>Click</button>
<div onClick={() => handleItemClick(item)}>Item</div>
```

### Input Events

```javascript
const handleInputChange = (event) => {
  setValue(event.target.value)
}

const handleCheckboxChange = (event) => {
  setChecked(event.target.checked)
}

const handleFileChange = (event) => {
  setFile(event.target.files[0])
}
```

---

## List Rendering

### Basic List

```javascript
{items.map(item => (
  <div key={item.id}>
    {item.name}
  </div>
))}
```

### List with Index

```javascript
{items.map((item, index) => (
  <div key={item.id || index}>
    {index + 1}. {item.name}
  </div>
))}
```

### Empty List

```javascript
{items.length === 0 ? (
  <p>No items found</p>
) : (
  <ul>
    {items.map(item => (
      <li key={item.id}>{item.name}</li>
    ))}
  </ul>
)}
```

---

## Complete Example

### Research Page Component

```javascript
import { useState, useEffect } from 'react'

function Research() {
  const API_BASE_URL = 'http://localhost:8080'

  // State
  const [sessions, setSessions] = useState([])
  const [selectedSession, setSelectedSession] = useState('')
  const [messages, setMessages] = useState([])
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load sessions on mount
  useEffect(() => {
    loadSessions()
  }, [])

  // Load messages when session changes
  useEffect(() => {
    if (selectedSession) {
      loadMessages(selectedSession)
    }
  }, [selectedSession])

  // API calls
  const loadSessions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/research/sessions`)
      const data = await response.json()
      setSessions(data.sessions)

      if (data.sessions.length > 0) {
        setSelectedSession(data.sessions[0])
      }
    } catch (err) {
      setError('Failed to load sessions')
    }
  }

  const loadMessages = async (sessionId) => {
    setIsLoading(true)
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/research/history/${sessionId}`
      )
      const data = await response.json()
      setMessages(data.messages)
    } catch (err) {
      setError('Failed to load messages')
    } finally {
      setIsLoading(false)
    }
  }

  const submitQuery = async () => {
    if (!query.trim()) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/research/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: query,
          session_id: selectedSession
        })
      })

      const data = await response.json()

      setMessages(prev => [
        ...prev,
        { role: 'user', content: query },
        { role: 'assistant', content: data.output }
      ])

      setQuery('')
    } catch (err) {
      setError('Failed to submit query')
    } finally {
      setIsLoading(false)
    }
  }

  // Event handlers
  const handleSessionChange = (event) => {
    setSelectedSession(event.target.value)
  }

  const handleQueryChange = (event) => {
    setQuery(event.target.value)
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    submitQuery()
  }

  // Render
  return (
    <div className="research-page">
      <h1>Story Research</h1>

      {/* Session selector */}
      <div className="session-selector">
        <label>Session:</label>
        <select value={selectedSession} onChange={handleSessionChange}>
          {sessions.map(session => (
            <option key={session} value={session}>
              {session}
            </option>
          ))}
        </select>
      </div>

      {/* Error display */}
      {error && <div className="error">{error}</div>}

      {/* Messages */}
      <div className="messages">
        {isLoading && messages.length === 0 && <p>Loading...</p>}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <strong>{msg.role}:</strong> {msg.content}
          </div>
        ))}
      </div>

      {/* Query form */}
      <form onSubmit={handleSubmit} className="query-form">
        <input
          type="text"
          value={query}
          onChange={handleQueryChange}
          placeholder="Enter research query..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !query.trim()}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  )
}

export default Research
```

---

## Styling Patterns

### CSS Classes

```javascript
// Static class
<div className="card">Content</div>

// Conditional class
<div className={isActive ? 'card active' : 'card'}>Content</div>

// Multiple conditional classes
<div className={`card ${isActive ? 'active' : ''} ${isHighlighted ? 'highlighted' : ''}`}>
  Content
</div>
```

### Inline Styles

```javascript
// Static style
<div style={{ padding: '20px', margin: '10px' }}>Content</div>

// Dynamic style
<div style={{ color: isError ? 'red' : 'black' }}>Content</div>

// Computed style
const cardStyle = {
  width: `${width}px`,
  backgroundColor: isActive ? '#007bff' : '#6c757d'
}
<div style={cardStyle}>Content</div>
```

---

## Best Practices

**DO:**
- Use functional components with hooks
- Declare all state at the top
- Group related state together
- Use descriptive variable names
- Handle errors gracefully
- Clean up effects (return cleanup function)
- Use keys in lists

**DON'T:**
- Mutate state directly
- Call hooks conditionally
- Forget dependencies in useEffect
- Use inline functions in render for performance-critical code
- Forget to handle loading/error states
- Use index as key unless list is static

---

## Related Documentation

- `api_communication.md` - API calling patterns
- `state_management.md` - State management with hooks
- `form_handling.md` - Form validation and submission
- `../COMMON.md` - Shared web patterns
