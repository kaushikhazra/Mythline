import React, { useState, useRef, useEffect } from 'react'

function SimpleResearch() {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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

      if (!sessionId) setSessionId(data.session_id)
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
        {sessionId && (
          <span className="badge badge-info">Session: {sessionId}</span>
        )}
        <button onClick={createNewSession}>New Session</button>
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
