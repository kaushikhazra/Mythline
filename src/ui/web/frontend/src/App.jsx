import React, { useState } from 'react'
import SimpleResearch from './pages/SimpleResearch'
import SimpleStoryCreator from './pages/SimpleStoryCreator'
import SimpleStoryViewer from './pages/SimpleStoryViewer'

function App() {
  const [page, setPage] = useState('research')

  return (
    <div>
      <div className="nav-tabs">
        <button
          className={page === 'research' ? 'active' : ''}
          onClick={() => setPage('research')}
        >
          Research
        </button>
        <button
          className={page === 'story' ? 'active' : ''}
          onClick={() => setPage('story')}
        >
          Create Story
        </button>
        <button
          className={page === 'viewer' ? 'active' : ''}
          onClick={() => setPage('viewer')}
        >
          View Stories
        </button>
      </div>
      {page === 'research' && <SimpleResearch />}
      {page === 'story' && <SimpleStoryCreator />}
      {page === 'viewer' && <SimpleStoryViewer />}
    </div>
  )
}

export default App
