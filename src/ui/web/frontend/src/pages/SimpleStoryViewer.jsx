import React, { useState, useEffect } from 'react'

function SimpleStoryViewer() {
  const [storyList, setStoryList] = useState([])
  const [selectedStory, setSelectedStory] = useState(null)
  const [storyContent, setStoryContent] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchStoryList()
  }, [])

  const fetchStoryList = async () => {
    try {
      const response = await fetch('/api/stories/list')
      const data = await response.json()
      setStoryList(data)
      if (data.length > 0) {
        loadStory(data[0])
      }
    } catch (error) {
      console.error('Error fetching story list:', error)
    }
  }

  const loadStory = async (subject) => {
    setLoading(true)
    setSelectedStory(subject)
    try {
      const response = await fetch(`/api/stories/${subject}`)
      const data = await response.json()
      setStoryContent(data)
    } catch (error) {
      console.error('Error loading story:', error)
    } finally {
      setLoading(false)
    }
  }

  const renderDialogue = (lines) => {
    if (!lines || lines.length === 0) return null
    return (
      <div className="dialogue-section">
        {lines.map((line, idx) => (
          <div key={idx} className="dialogue-line">
            <span className="dialogue-actor">{line.actor}:</span>
            <span className="dialogue-text">{line.line}</span>
          </div>
        ))}
      </div>
    )
  }

  const renderSegment = (segment, index) => {
    const questIds = segment.quest_ids?.join(', ') || ''
    const phase = segment.phase || ''
    const section = segment.section || ''
    const sectionLabel = `${phase.charAt(0).toUpperCase() + phase.slice(1)} - ${section.charAt(0).toUpperCase() + section.slice(1)}`

    return (
      <div key={index} className="quest-section">
        <h3 className="segment-header">
          <span className="quest-ids">[{questIds}]</span>
          {sectionLabel}
        </h3>

        {segment.text && (
          <div className="narrative-section">
            <p className="narrative-text">{segment.text}</p>
          </div>
        )}

        {segment.lines && segment.lines.length > 0 && (
          <div className="dialogue-container">
            {renderDialogue(segment.lines)}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="story-viewer-container">
      <div className="story-sidebar">
        <h2>Available Stories</h2>
        {storyList.length === 0 ? (
          <p className="no-stories">No stories available</p>
        ) : (
          storyList.map((story) => (
            <button
              key={story}
              className={`story-item ${selectedStory === story ? 'active' : ''}`}
              onClick={() => loadStory(story)}
            >
              {story}
            </button>
          ))
        )}
      </div>

      <div className="story-content">
        {loading ? (
          <div className="loading-message">Loading story...</div>
        ) : storyContent ? (
          <>
            <h1 className="story-title">{storyContent.title}</h1>

            {storyContent.introduction && (
              <div className="introduction-section">
                <p className="narrative-text">{storyContent.introduction.text}</p>
              </div>
            )}

            {storyContent.segments && storyContent.segments.map((segment, index) =>
              renderSegment(segment, index)
            )}

            {storyContent.conclusion && (
              <div className="conclusion-section">
                <h2>Conclusion</h2>
                <p className="narrative-text">{storyContent.conclusion.text}</p>
              </div>
            )}
          </>
        ) : (
          <div className="no-selection">Select a story to view</div>
        )}
      </div>
    </div>
  )
}

export default SimpleStoryViewer
