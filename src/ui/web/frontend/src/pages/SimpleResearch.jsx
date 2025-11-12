import React, { useState, useRef, useEffect } from 'react'

function SimpleResearch() {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [availableSessions, setAvailableSessions] = useState([])
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    fetchSessions()
  }, [])

  const fetchSessions = async () => {
    try {
      const response = await fetch('/api/research/sessions')
      const sessions = await response.json()
      setAvailableSessions(sessions)
    } catch (error) {
      console.error('Failed to fetch sessions:', error)
    }
  }

  const loadSession = async (selectedSessionId) => {
    if (!selectedSessionId) return

    try {
      const response = await fetch(`/api/research/sessions/${selectedSessionId}`)
      const data = await response.json()

      setSessionId(data.session_id)
      setMessages(data.messages)
      setInput('')
    } catch (error) {
      console.error('Failed to load session:', error)
    }
  }

  const createNewSession = () => {
    setSessionId(null)
    setMessages([])
    setInput('')
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    setLoading(true)
    const userMessage = input
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setInput('')

    try {
      const body = sessionId
        ? { message: userMessage, session_id: sessionId }
        : { message: userMessage }

      const response = await fetch('/api/research/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      const text = await response.text()
      const data = JSON.parse(text)

      if (!sessionId) {
        setSessionId(data.session_id)
        fetchSessions()
      }
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
    } catch (error) {
      setMessages(prev => [...prev, { role: 'error', content: 'Error: ' + error.message }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-container">
      <h1>Research Chat</h1>

      <div className="chat-header">
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          {availableSessions.length > 0 && (
            <select
              value={sessionId || ''}
              onChange={(e) => loadSession(e.target.value)}
              style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            >
              <option value="">Select a session...</option>
              {availableSessions.map((session) => (
                <option key={session.session_id} value={session.session_id}>
                  {session.session_id} ({session.message_count} messages)
                </option>
              ))}
            </select>
          )}
          {sessionId && (
            <span className="badge badge-info">Current: {sessionId}</span>
          )}
          <button onClick={createNewSession}>New Session</button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <strong>{msg.role === 'user' ? 'You' : 'Agent'}</strong>
            <div>{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <strong>Agent</strong>
            <div>Thinking...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="chat-input-form">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask about WoW lore..."
          disabled={loading}
          rows={3}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  )
}

export default SimpleResearch
