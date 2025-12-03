# Frontend: Form Handling

Building forms with validation and submission in React.

---

## Overview

**Use when:** User input forms, data submission, multi-step forms, file uploads.

**Pattern:**
```
Form State → Validation → Submission → Error Handling → Success
```

---

## Basic Form Pattern

### Controlled Form

```javascript
import { useState } from 'react'

function BasicForm() {
  const [formData, setFormData] = useState({
    name: '',
    email: ''
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleChange = (event) => {
    const { name, value } = event.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setIsSubmitting(true)

    try {
      const response = await fetch('/api/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      const data = await response.json()
      console.log('Success:', data)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        name="name"
        value={formData.name}
        onChange={handleChange}
        placeholder="Name"
      />

      <input
        type="email"
        name="email"
        value={formData.email}
        onChange={handleChange}
        placeholder="Email"
      />

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting...' : 'Submit'}
      </button>
    </form>
  )
}
```

---

## Input Types

### Text Input

```javascript
<input
  type="text"
  name="username"
  value={formData.username}
  onChange={handleChange}
  placeholder="Enter username"
  required
/>
```

### Email Input

```javascript
<input
  type="email"
  name="email"
  value={formData.email}
  onChange={handleChange}
  placeholder="user@example.com"
/>
```

### Password Input

```javascript
<input
  type="password"
  name="password"
  value={formData.password}
  onChange={handleChange}
  placeholder="Enter password"
  minLength={8}
/>
```

### Number Input

```javascript
<input
  type="number"
  name="age"
  value={formData.age}
  onChange={handleChange}
  min={0}
  max={120}
/>
```

### Checkbox

```javascript
const [isChecked, setIsChecked] = useState(false)

<input
  type="checkbox"
  checked={isChecked}
  onChange={(e) => setIsChecked(e.target.checked)}
/>

// Multiple checkboxes
const handleCheckboxChange = (event) => {
  const { name, checked } = event.target
  setFormData(prev => ({
    ...prev,
    [name]: checked
  }))
}

<input
  type="checkbox"
  name="newsletter"
  checked={formData.newsletter}
  onChange={handleCheckboxChange}
/>
```

### Radio Buttons

```javascript
<div>
  <label>
    <input
      type="radio"
      name="plan"
      value="basic"
      checked={formData.plan === 'basic'}
      onChange={handleChange}
    />
    Basic
  </label>

  <label>
    <input
      type="radio"
      name="plan"
      value="premium"
      checked={formData.plan === 'premium'}
      onChange={handleChange}
    />
    Premium
  </label>
</div>
```

### Select Dropdown

```javascript
<select
  name="country"
  value={formData.country}
  onChange={handleChange}
>
  <option value="">Select country</option>
  <option value="us">United States</option>
  <option value="uk">United Kingdom</option>
  <option value="ca">Canada</option>
</select>
```

### Textarea

```javascript
<textarea
  name="message"
  value={formData.message}
  onChange={handleChange}
  placeholder="Enter message"
  rows={5}
/>
```

### File Input

```javascript
const [file, setFile] = useState(null)

const handleFileChange = (event) => {
  setFile(event.target.files[0])
}

<input
  type="file"
  onChange={handleFileChange}
  accept=".txt,.md"
/>
```

---

## Form Validation

### Client-Side Validation

```javascript
function ValidatedForm() {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  })
  const [errors, setErrors] = useState({})

  const validate = () => {
    const newErrors = {}

    // Email validation
    if (!formData.email) {
      newErrors.email = 'Email is required'
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email is invalid'
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = 'Password is required'
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters'
    }

    return newErrors
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    const validationErrors = validate()

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setErrors({})
    // Submit form
  }

  const handleChange = (event) => {
    const { name, value } = event.target
    setFormData(prev => ({ ...prev, [name]: value }))

    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <input
          type="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          className={errors.email ? 'error' : ''}
        />
        {errors.email && <span className="error">{errors.email}</span>}
      </div>

      <div>
        <input
          type="password"
          name="password"
          value={formData.password}
          onChange={handleChange}
          className={errors.password ? 'error' : ''}
        />
        {errors.password && <span className="error">{errors.password}</span>}
      </div>

      <button type="submit">Submit</button>
    </form>
  )
}
```

### Real-Time Validation

```javascript
const [touched, setTouched] = useState({})

const handleBlur = (event) => {
  const { name } = event.target
  setTouched(prev => ({ ...prev, [name]: true }))
}

// Show error only after field has been touched
{touched.email && errors.email && (
  <span className="error">{errors.email}</span>
)}

<input
  name="email"
  value={formData.email}
  onChange={handleChange}
  onBlur={handleBlur}
/>
```

---

## Form State Patterns

### Reset Form

```javascript
const initialState = {
  name: '',
  email: '',
  message: ''
}

const [formData, setFormData] = useState(initialState)

const resetForm = () => {
  setFormData(initialState)
  setErrors({})
}

const handleSubmit = async (event) => {
  event.preventDefault()
  await submitForm(formData)
  resetForm()
}
```

### Disable Submit Button

```javascript
const isFormValid = () => {
  return (
    formData.email &&
    formData.password &&
    Object.keys(errors).length === 0
  )
}

<button type="submit" disabled={!isFormValid() || isSubmitting}>
  Submit
</button>
```

### Loading State

```javascript
const [isSubmitting, setIsSubmitting] = useState(false)

const handleSubmit = async (event) => {
  event.preventDefault()
  setIsSubmitting(true)

  try {
    await api.submit(formData)
  } finally {
    setIsSubmitting(false)
  }
}

// Disable all inputs during submission
<input
  name="field"
  value={formData.field}
  onChange={handleChange}
  disabled={isSubmitting}
/>
```

---

## Advanced Patterns

### Dynamic Fields

```javascript
const [items, setItems] = useState([''])

const addItem = () => {
  setItems(prev => [...prev, ''])
}

const removeItem = (index) => {
  setItems(prev => prev.filter((_, idx) => idx !== index))
}

const updateItem = (index, value) => {
  setItems(prev =>
    prev.map((item, idx) => (idx === index ? value : item))
  )
}

return (
  <div>
    {items.map((item, index) => (
      <div key={index}>
        <input
          value={item}
          onChange={(e) => updateItem(index, e.target.value)}
        />
        <button onClick={() => removeItem(index)}>Remove</button>
      </div>
    ))}
    <button onClick={addItem}>Add Item</button>
  </div>
)
```

### Multi-Step Form

```javascript
function MultiStepForm() {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    // Step 1
    name: '',
    email: '',
    // Step 2
    address: '',
    city: ''
  })

  const nextStep = () => setStep(prev => prev + 1)
  const prevStep = () => setStep(prev => prev - 1)

  const handleChange = (event) => {
    const { name, value } = event.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    if (step < 2) {
      nextStep()
    } else {
      // Submit final form
      submitForm(formData)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {step === 1 && (
        <div>
          <h2>Step 1: Personal Info</h2>
          <input
            name="name"
            value={formData.name}
            onChange={handleChange}
          />
          <input
            name="email"
            value={formData.email}
            onChange={handleChange}
          />
        </div>
      )}

      {step === 2 && (
        <div>
          <h2>Step 2: Address</h2>
          <input
            name="address"
            value={formData.address}
            onChange={handleChange}
          />
          <input
            name="city"
            value={formData.city}
            onChange={handleChange}
          />
        </div>
      )}

      <div>
        {step > 1 && <button type="button" onClick={prevStep}>Back</button>}
        <button type="submit">
          {step < 2 ? 'Next' : 'Submit'}
        </button>
      </div>
    </form>
  )
}
```

---

## File Upload

### Single File Upload

```javascript
function FileUploadForm() {
  const [file, setFile] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState(null)

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0]

    // Validate file
    if (selectedFile && selectedFile.size > 5 * 1024 * 1024) {
      setError('File size must be less than 5MB')
      return
    }

    setFile(selectedFile)
    setError(null)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!file) {
      setError('Please select a file')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    setIsUploading(true)
    setError(null)

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      })

      const data = await response.json()
      console.log('Upload success:', data)
      setFile(null)
    } catch (err) {
      setError('Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="file"
        onChange={handleFileChange}
        accept=".jpg,.png,.pdf"
      />

      {file && <p>Selected: {file.name}</p>}
      {error && <p className="error">{error}</p>}

      <button type="submit" disabled={!file || isUploading}>
        {isUploading ? 'Uploading...' : 'Upload'}
      </button>
    </form>
  )
}
```

### Multiple Files Upload

```javascript
const [files, setFiles] = useState([])

const handleFilesChange = (event) => {
  const selectedFiles = Array.from(event.target.files)
  setFiles(selectedFiles)
}

const handleSubmit = async (event) => {
  event.preventDefault()

  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file)
  })

  await fetch('/api/upload-multiple', {
    method: 'POST',
    body: formData
  })
}

<input
  type="file"
  multiple
  onChange={handleFilesChange}
/>

{files.length > 0 && (
  <ul>
    {files.map((file, idx) => (
      <li key={idx}>{file.name}</li>
    ))}
  </ul>
)}
```

---

## Form Submission Patterns

### Basic Submission

```javascript
const handleSubmit = async (event) => {
  event.preventDefault()

  const response = await fetch('/api/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
  })

  const data = await response.json()
  console.log('Success:', data)
}
```

### With Error Handling

```javascript
const [submitError, setSubmitError] = useState(null)
const [submitSuccess, setSubmitSuccess] = useState(false)

const handleSubmit = async (event) => {
  event.preventDefault()
  setSubmitError(null)
  setSubmitSuccess(false)
  setIsSubmitting(true)

  try {
    const response = await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Submission failed')
    }

    const data = await response.json()
    setSubmitSuccess(true)
    resetForm()
  } catch (err) {
    setSubmitError(err.message)
  } finally {
    setIsSubmitting(false)
  }
}

// Render
{submitError && <div className="error">{submitError}</div>}
{submitSuccess && <div className="success">Form submitted successfully!</div>}
```

### With Redirect

```javascript
import { useNavigate } from 'react-router-dom'

function MyForm() {
  const navigate = useNavigate()

  const handleSubmit = async (event) => {
    event.preventDefault()

    const response = await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    })

    const data = await response.json()

    // Redirect to success page
    navigate('/success', { state: { data } })
  }

  return <form onSubmit={handleSubmit}>{/* ... */}</form>
}
```

---

## Complete Example

### Story Subject Form

```javascript
import { useState } from 'react'

function StorySubjectForm({ onSubmit }) {
  const [formData, setFormData] = useState({
    subject: '',
    sessionId: ''
  })
  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const validate = () => {
    const newErrors = {}

    if (!formData.subject.trim()) {
      newErrors.subject = 'Subject is required'
    } else if (formData.subject.length < 3) {
      newErrors.subject = 'Subject must be at least 3 characters'
    }

    return newErrors
  }

  const handleChange = (event) => {
    const { name, value } = event.target
    setFormData(prev => ({ ...prev, [name]: value }))

    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    const validationErrors = validate()

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setErrors({})
    setSubmitError(null)
    setIsSubmitting(true)

    try {
      const response = await fetch('http://localhost:8080/api/story/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: formData.subject,
          session_id: formData.sessionId || `session_${Date.now()}`
        })
      })

      if (!response.ok) {
        throw new Error('Failed to start story generation')
      }

      const data = await response.json()
      onSubmit(data)

      // Reset form
      setFormData({ subject: '', sessionId: '' })
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const isFormValid = formData.subject.trim().length >= 3

  return (
    <form onSubmit={handleSubmit} className="story-form">
      <div className="form-group">
        <label htmlFor="subject">Story Subject</label>
        <input
          id="subject"
          type="text"
          name="subject"
          value={formData.subject}
          onChange={handleChange}
          placeholder="e.g., Shadowglen, Durotar"
          disabled={isSubmitting}
          className={errors.subject ? 'error' : ''}
        />
        {errors.subject && (
          <span className="error-message">{errors.subject}</span>
        )}
      </div>

      <div className="form-group">
        <label htmlFor="sessionId">Session ID (optional)</label>
        <input
          id="sessionId"
          type="text"
          name="sessionId"
          value={formData.sessionId}
          onChange={handleChange}
          placeholder="Leave empty for auto-generated"
          disabled={isSubmitting}
        />
      </div>

      {submitError && (
        <div className="error-banner">{submitError}</div>
      )}

      <button
        type="submit"
        disabled={!isFormValid || isSubmitting}
        className="submit-button"
      >
        {isSubmitting ? 'Starting Generation...' : 'Generate Story'}
      </button>
    </form>
  )
}

export default StorySubjectForm
```

---

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Best Practices

**DO:**
- Use controlled components (value + onChange)
- Validate on submit and optionally on blur
- Disable submit while submitting
- Provide clear error messages
- Clear errors when user corrects input
- Reset form after successful submission
- Use appropriate input types

**DON'T:**
- Forget to preventDefault on submit
- Validate on every keystroke (impacts UX)
- Submit without validation
- Mutate form state directly
- Forget to handle loading states
- Show all errors before user interaction

---

## Related Documentation

- `page_component.md` - Component structure
- `state_management.md` - Managing state
- `api_communication.md` - Submitting forms to API
- `../COMMON.md` - Common patterns
