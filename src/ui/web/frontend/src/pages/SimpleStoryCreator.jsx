import React, { useState, useRef, useEffect } from 'react'

function SimpleStoryCreator() {
  const [subjects, setSubjects] = useState([])
  const [subject, setSubject] = useState('')
  const [player, setPlayer] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [progress, setProgress] = useState(null)
  const pollIntervalRef = useRef(null)

  useEffect(() => {
    fetchSubjects()
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

  const fetchSubjects = async () => {
    try {
      const response = await fetch('/api/research/subjects')
      const data = await response.json()
      setSubjects(data)
      if (data.length > 0) {
        setSubject(data[0])
        checkJobStatus(data[0])
      }
    } catch (error) {
      console.error('Error fetching subjects:', error)
    }
  }

  const handleSubjectChange = (newSubject) => {
    setSubject(newSubject)
    checkJobStatus(newSubject)
  }

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

      if (data.status === 'in_progress' || data.status === 'starting' || data.status === 'planning') {
        setLoading(true)
        setProgress(data)
        setMessage(data.message)
        startPolling(subjectName)
      }
    } catch (err) {
      // No job found - stay in create mode
    }
  }

  const getStepLabel = (details) => {
    if (!details) return 'Processing...'
    const { segment_type, sub_type, quest_name } = details

    const labels = {
      'introduction': 'Introduction',
      'conclusion': 'Conclusion',
      'quest_introduction': 'Quest Introduction',
      'quest_dialogue': 'Quest Dialogue',
      'quest_execution': 'Quest Execution',
      'quest_conclusion': 'Quest Completion'
    }

    if (segment_type === 'quest' && sub_type) {
      const label = labels[sub_type] || sub_type
      return quest_name ? `${label}: ${quest_name}` : label
    }

    return labels[segment_type] || segment_type || 'Processing...'
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
          <select
            value={subject}
            onChange={(e) => handleSubjectChange(e.target.value)}
            disabled={loading}
          >
            {subjects.length === 0 ? (
              <option value="">No subjects available</option>
            ) : (
              subjects.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))
            )}
          </select>
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

      {loading && progress && (
        <div className="progress-container">
          <h3>{progress.status === 'planning' ? 'Planning Story' : 'Generating Story'}</h3>

          {progress.status === 'planning' ? (
            <>
              <p><strong>Planning:</strong> {progress.details?.segment || 'Initializing...'}</p>
              {progress.details?.quest_phase && (
                <p className="progress-text">Phase: {progress.details.quest_phase}</p>
              )}
              <p className="progress-text">{message}</p>
            </>
          ) : (
            <>
              <div className="progress-bar">
                <div
                  className="progress-bar-fill"
                  style={{ width: progress.total > 0 ? `${(progress.current / progress.total) * 100}%` : '0%' }}
                />
              </div>
              <p className="progress-text">
                Step {progress.current} of {progress.total}
              </p>
              <p><strong>Current Step:</strong> {getStepLabel(progress.details)}</p>
              {message && <p className="progress-text">{message}</p>}
            </>
          )}
        </div>
      )}

      {!loading && message && (
        <div className={`message ${message.startsWith('Error') ? 'error' : 'success'}`}>
          <strong>{message.startsWith('Error') ? 'Error' : 'Status'}</strong>
          <div>{message}</div>
        </div>
      )}
    </div>
  )
}

export default SimpleStoryCreator
