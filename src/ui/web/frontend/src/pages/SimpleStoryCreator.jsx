import React, { useState, useRef, useEffect } from 'react'

function SimpleStoryCreator() {
  const [subject, setSubject] = useState('')
  const [player, setPlayer] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [progress, setProgress] = useState(null)
  const pollIntervalRef = useRef(null)

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

  const startPolling = (jobSubject) => {
    pollIntervalRef.current = setInterval(async () => {
      try {
        const progressRes = await fetch(`/api/story/progress/${jobSubject}`)
        const progressData = await progressRes.json()

        setProgress(progressData)
        setMessage(progressData.message)

        if (progressData.status === 'complete') {
          clearInterval(pollIntervalRef.current)
          setLoading(false)
          setMessage('Story creation complete!')
        } else if (progressData.status === 'error') {
          clearInterval(pollIntervalRef.current)
          setLoading(false)
          setMessage('Error: ' + progressData.message)
        }
      } catch (err) {
        console.error('Poll error:', err)
      }
    }, 2000)
  }

  const checkJobStatus = async (subjectName) => {
    if (!subjectName.trim()) return

    try {
      const res = await fetch(`/api/story/progress/${subjectName}`)
      const data = await res.json()

      if (data.status === 'in_progress' || data.status === 'starting') {
        setLoading(true)
        setProgress(data)
        setMessage(data.message)
        startPolling(subjectName)
      }
    } catch (err) {
      // No job found - stay in create mode
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!subject.trim() || !player.trim() || loading) return

    setLoading(true)
    setMessage('Starting story creation...')
    setProgress(null)

    try {
      const response = await fetch('/api/story/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject, player })
      })

      if (!response.ok) {
        const error = await response.json()
        setMessage('Error: ' + error.detail)
        setLoading(false)
        return
      }

      const data = await response.json()
      setMessage(data.message)

      startPolling(subject)

    } catch (error) {
      setMessage('Error: ' + error.message)
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>Create Story</h1>

      <form onSubmit={handleSubmit}>
        <div>
          <label>Subject: </label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            onBlur={() => checkJobStatus(subject)}
            placeholder="e.g., Goldshire"
            disabled={loading}
          />
        </div>
        <br />

        {!loading && (
          <>
            <div>
              <label>Player Name: </label>
              <input
                type="text"
                value={player}
                onChange={(e) => setPlayer(e.target.value)}
                placeholder="e.g., Sarephine"
              />
            </div>
            <br />
            <button type="submit">Create Story</button>
          </>
        )}

        {loading && (
          <p>Story creation in progress for: {subject}</p>
        )}
      </form>

      {message && (
        <div>
          <h3>Status:</h3>
          <p>{message}</p>
        </div>
      )}

      {progress && progress.total > 0 && (
        <div>
          <h3>Progress:</h3>
          <p>{progress.current} / {progress.total}</p>
          {progress.details && progress.details.quest_name && (
            <p>Quest: {progress.details.quest_name}</p>
          )}
        </div>
      )}
    </div>
  )
}

export default SimpleStoryCreator
