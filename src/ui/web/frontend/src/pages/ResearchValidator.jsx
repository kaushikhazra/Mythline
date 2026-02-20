import React, { useState, useEffect } from 'react'

function ResearchValidator() {
  const [subjects, setSubjects] = useState([])
  const [selectedSubject, setSelectedSubject] = useState(null)
  const [researchData, setResearchData] = useState(null)
  const [activeTab, setActiveTab] = useState('setting')
  const [hasChanges, setHasChanges] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(false)
  const [expandedQuest, setExpandedQuest] = useState(null)
  const [expandedNpc, setExpandedNpc] = useState(null)
  const [message, setMessage] = useState(null)

  useEffect(() => {
    fetchSubjects()
  }, [])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        if (hasChanges && !saving && researchData) {
          handleSave()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [hasChanges, saving, researchData])

  const fetchSubjects = async () => {
    try {
      const response = await fetch('/api/research/subjects')
      const data = await response.json()
      setSubjects(data)
      if (data.length > 0) {
        loadSubject(data[0])
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to fetch subjects: ' + error.message })
    }
  }

  const loadSubject = async (subject) => {
    setLoading(true)
    setSelectedSubject(subject)
    setHasChanges(false)
    setExpandedQuest(null)
    try {
      const response = await fetch(`/api/research/${subject}/data`)
      if (!response.ok) {
        throw new Error('Research data not found')
      }
      const data = await response.json()
      setResearchData(data)
      setMessage(null)
    } catch (error) {
      setResearchData(null)
      setMessage({ type: 'error', text: error.message })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!selectedSubject || !researchData) return
    setSaving(true)
    try {
      const response = await fetch(`/api/research/${selectedSubject}/data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(researchData)
      })
      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Save failed')
      }
      setHasChanges(false)
      setMessage({ type: 'success', text: 'Changes saved successfully' })
    } catch (error) {
      setMessage({ type: 'error', text: 'Save failed: ' + error.message })
    } finally {
      setSaving(false)
    }
  }

  const updateField = (path, value) => {
    setResearchData(prev => {
      const updated = JSON.parse(JSON.stringify(prev))
      const parts = path.split('.')
      let obj = updated
      for (let i = 0; i < parts.length - 1; i++) {
        const key = isNaN(parts[i]) ? parts[i] : parseInt(parts[i])
        obj = obj[key]
      }
      const lastKey = isNaN(parts[parts.length - 1]) ? parts[parts.length - 1] : parseInt(parts[parts.length - 1])
      obj[lastKey] = value
      return updated
    })
    setHasChanges(true)
  }

  const renderSettingTab = () => {
    if (!researchData?.setting) return <p>No setting data</p>
    const s = researchData.setting
    return (
      <div className="validator-form">
        <div className="form-group">
          <label>Zone</label>
          <input
            type="text"
            value={s.zone || ''}
            onChange={(e) => updateField('setting.zone', e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Starting Location</label>
          <input
            type="text"
            value={s.starting_location || ''}
            onChange={(e) => updateField('setting.starting_location', e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Journey</label>
          <textarea
            value={s.journey || ''}
            onChange={(e) => updateField('setting.journey', e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Description</label>
          <textarea
            value={s.description || ''}
            onChange={(e) => updateField('setting.description', e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Lore Context</label>
          <textarea
            value={s.lore_context || ''}
            onChange={(e) => updateField('setting.lore_context', e.target.value)}
          />
        </div>
      </div>
    )
  }

  const renderLocationFields = (basePath, location, isExecution = false) => {
    return (
      <div className="location-section">
        <h5>Location</h5>
        <div className="location-grid">
          <div className="form-group">
            <label>Area Name</label>
            <input
              type="text"
              value={location.area?.name || ''}
              onChange={(e) => updateField(`${basePath}.area.name`, e.target.value)}
            />
          </div>
          <div className="form-group coord-group">
            <label>X</label>
            <input
              type="number"
              step="0.01"
              value={location.area?.x ?? ''}
              onChange={(e) => updateField(`${basePath}.area.x`, e.target.value ? parseFloat(e.target.value) : null)}
            />
          </div>
          <div className="form-group coord-group">
            <label>Y</label>
            <input
              type="number"
              step="0.01"
              value={location.area?.y ?? ''}
              onChange={(e) => updateField(`${basePath}.area.y`, e.target.value ? parseFloat(e.target.value) : null)}
            />
          </div>
        </div>
        {!isExecution && (
          <div className="form-group">
            <label>Position</label>
            <textarea
              value={location.position || ''}
              onChange={(e) => updateField(`${basePath}.position`, e.target.value)}
            />
          </div>
        )}
        <div className="form-group">
          <label>Visual</label>
          <textarea
            value={location.visual || ''}
            onChange={(e) => updateField(`${basePath}.visual`, e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Landmarks</label>
          <textarea
            value={location.landmarks || ''}
            onChange={(e) => updateField(`${basePath}.landmarks`, e.target.value)}
          />
        </div>
        {isExecution && (
          <div className="form-group">
            <label>Enemies</label>
            <textarea
              value={location.enemies || ''}
              onChange={(e) => updateField(`${basePath}.enemies`, e.target.value)}
            />
          </div>
        )}
      </div>
    )
  }

  const renderNpcFields = (basePath, npc, title) => {
    return (
      <div className="npc-section">
        <h4>{title}</h4>
        <div className="form-row">
          <div className="form-group">
            <label>Name</label>
            <input
              type="text"
              value={npc.name || ''}
              onChange={(e) => updateField(`${basePath}.name`, e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Title</label>
            <input
              type="text"
              value={npc.title || ''}
              onChange={(e) => updateField(`${basePath}.title`, e.target.value)}
            />
          </div>
        </div>
        <div className="form-group">
          <label>Personality</label>
          <textarea
            value={npc.personality || ''}
            onChange={(e) => updateField(`${basePath}.personality`, e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Lore</label>
          <textarea
            value={npc.lore || ''}
            onChange={(e) => updateField(`${basePath}.lore`, e.target.value)}
          />
        </div>
        {npc.location && renderLocationFields(`${basePath}.location`, npc.location)}
      </div>
    )
  }

  const renderQuestCard = (quest, index) => {
    const isExpanded = expandedQuest === index
    return (
      <div key={index} className="quest-card">
        <div
          className="quest-card-header"
          onClick={() => setExpandedQuest(isExpanded ? null : index)}
        >
          <span className="quest-id">[{quest.id}]</span>
          <span className="quest-title-text">{quest.title}</span>
          <span className="expand-icon">{isExpanded ? '−' : '+'}</span>
        </div>
        {isExpanded && (
          <div className="quest-card-body">
            <div className="form-section">
              <h4>Basic Info</h4>
              <div className="form-group">
                <label>Title</label>
                <input
                  type="text"
                  value={quest.title || ''}
                  onChange={(e) => updateField(`quests.${index}.title`, e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Story Beat</label>
                <textarea
                  value={quest.story_beat || ''}
                  onChange={(e) => updateField(`quests.${index}.story_beat`, e.target.value)}
                />
              </div>
            </div>

            <div className="form-section">
              <h4>Objectives</h4>
              <div className="form-group">
                <label>Summary</label>
                <textarea
                  value={quest.objectives?.summary || ''}
                  onChange={(e) => updateField(`quests.${index}.objectives.summary`, e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Details</label>
                <textarea
                  value={quest.objectives?.details || ''}
                  onChange={(e) => updateField(`quests.${index}.objectives.details`, e.target.value)}
                />
              </div>
            </div>

            {quest.quest_giver && renderNpcFields(`quests.${index}.quest_giver`, quest.quest_giver, 'Quest Giver')}
            {quest.turn_in_npc && renderNpcFields(`quests.${index}.turn_in_npc`, quest.turn_in_npc, 'Turn-in NPC')}

            <div className="form-section execution-location">
              <h4>Execution Location</h4>
              {quest.execution_location && renderLocationFields(
                `quests.${index}.execution_location`,
                quest.execution_location,
                true
              )}
            </div>

            <div className="form-section">
              <h4>Story Text</h4>
              <div className="form-group">
                <textarea
                  value={quest.story_text || ''}
                  onChange={(e) => updateField(`quests.${index}.story_text`, e.target.value)}
                  rows={6}
                />
              </div>
            </div>

            <div className="form-section">
              <h4>Completion Text</h4>
              <div className="form-group">
                <textarea
                  value={quest.completion_text || ''}
                  onChange={(e) => updateField(`quests.${index}.completion_text`, e.target.value)}
                  rows={6}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  const renderQuestsTab = () => {
    if (!researchData?.quests || researchData.quests.length === 0) {
      return <p>No quests data</p>
    }
    return (
      <div className="quests-list">
        {researchData.quests.map((quest, index) => renderQuestCard(quest, index))}
      </div>
    )
  }

  const renderRoleplayTab = () => {
    if (!researchData) return <p>No data</p>
    const roleplay = researchData.roleplay || {}
    const keys = Object.keys(roleplay)

    const updateRoleplayKey = (oldKey, newKey) => {
      if (oldKey === newKey) return
      setResearchData(prev => {
        const updated = JSON.parse(JSON.stringify(prev))
        const value = updated.roleplay[oldKey]
        delete updated.roleplay[oldKey]
        updated.roleplay[newKey] = value
        return updated
      })
      setHasChanges(true)
    }

    const updateRoleplayValue = (key, value) => {
      setResearchData(prev => {
        const updated = JSON.parse(JSON.stringify(prev))
        updated.roleplay[key] = value
        return updated
      })
      setHasChanges(true)
    }

    const addRoleplayEntry = () => {
      const newKey = `new_entry_${Date.now()}`
      setResearchData(prev => {
        const updated = JSON.parse(JSON.stringify(prev))
        if (!updated.roleplay) updated.roleplay = {}
        updated.roleplay[newKey] = ''
        return updated
      })
      setHasChanges(true)
    }

    const deleteRoleplayEntry = (key) => {
      setResearchData(prev => {
        const updated = JSON.parse(JSON.stringify(prev))
        delete updated.roleplay[key]
        return updated
      })
      setHasChanges(true)
    }

    return (
      <div className="roleplay-editor">
        {keys.length === 0 ? (
          <p className="no-data">No roleplay entries</p>
        ) : (
          keys.map((key, index) => (
            <div key={index} className="roleplay-entry">
              <div className="roleplay-header">
                <input
                  type="text"
                  className="roleplay-key"
                  value={key}
                  onChange={(e) => updateRoleplayKey(key, e.target.value)}
                />
                <button
                  className="delete-btn"
                  onClick={() => deleteRoleplayEntry(key)}
                >
                  Delete
                </button>
              </div>
              <textarea
                value={roleplay[key] || ''}
                onChange={(e) => updateRoleplayValue(key, e.target.value)}
                rows={4}
              />
            </div>
          ))
        )}
        <button onClick={addRoleplayEntry} className="add-btn">
          Add Entry
        </button>
      </div>
    )
  }

  const getUniqueNpcs = () => {
    if (!researchData?.quests) return []
    const npcMap = new Map()

    researchData.quests.forEach((quest, questIndex) => {
      if (quest.quest_giver?.name) {
        const name = quest.quest_giver.name
        if (!npcMap.has(name)) {
          npcMap.set(name, { npc: quest.quest_giver, usages: [] })
        }
        npcMap.get(name).usages.push({ questIndex, questId: quest.id, role: 'Quest Giver' })
      }
      if (quest.turn_in_npc?.name) {
        const name = quest.turn_in_npc.name
        if (!npcMap.has(name)) {
          npcMap.set(name, { npc: quest.turn_in_npc, usages: [] })
        }
        npcMap.get(name).usages.push({ questIndex, questId: quest.id, role: 'Turn-in NPC' })
      }
    })

    return Array.from(npcMap.entries()).map(([name, data]) => ({
      name,
      npc: data.npc,
      usages: data.usages
    }))
  }

  const updateNpcField = (npcName, fieldPath, value) => {
    setResearchData(prev => {
      const updated = JSON.parse(JSON.stringify(prev))

      updated.quests.forEach((quest) => {
        if (quest.quest_giver?.name === npcName) {
          setNestedValue(quest.quest_giver, fieldPath, value)
        }
        if (quest.turn_in_npc?.name === npcName) {
          setNestedValue(quest.turn_in_npc, fieldPath, value)
        }
      })

      return updated
    })
    setHasChanges(true)
  }

  const setNestedValue = (obj, path, value) => {
    const parts = path.split('.')
    let current = obj
    for (let i = 0; i < parts.length - 1; i++) {
      if (!current[parts[i]]) current[parts[i]] = {}
      current = current[parts[i]]
    }
    current[parts[parts.length - 1]] = value
  }

  const renderNpcLocationFields = (npcName, location) => {
    return (
      <div className="location-section">
        <h5>Location</h5>
        <div className="location-grid">
          <div className="form-group">
            <label>Area Name</label>
            <input
              type="text"
              value={location?.area?.name || ''}
              onChange={(e) => updateNpcField(npcName, 'location.area.name', e.target.value)}
            />
          </div>
          <div className="form-group coord-group">
            <label>X</label>
            <input
              type="number"
              step="0.01"
              value={location?.area?.x ?? ''}
              onChange={(e) => updateNpcField(npcName, 'location.area.x', e.target.value ? parseFloat(e.target.value) : null)}
            />
          </div>
          <div className="form-group coord-group">
            <label>Y</label>
            <input
              type="number"
              step="0.01"
              value={location?.area?.y ?? ''}
              onChange={(e) => updateNpcField(npcName, 'location.area.y', e.target.value ? parseFloat(e.target.value) : null)}
            />
          </div>
        </div>
        <div className="form-group">
          <label>Position</label>
          <textarea
            value={location?.position || ''}
            onChange={(e) => updateNpcField(npcName, 'location.position', e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Visual</label>
          <textarea
            value={location?.visual || ''}
            onChange={(e) => updateNpcField(npcName, 'location.visual', e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Landmarks</label>
          <textarea
            value={location?.landmarks || ''}
            onChange={(e) => updateNpcField(npcName, 'location.landmarks', e.target.value)}
          />
        </div>
      </div>
    )
  }

  const renderNpcCard = (npcData, index) => {
    const isExpanded = expandedNpc === index
    const { name, npc, usages } = npcData

    return (
      <div key={index} className="npc-card">
        <div
          className="npc-card-header"
          onClick={() => setExpandedNpc(isExpanded ? null : index)}
        >
          <div className="npc-header-info">
            <span className="npc-name">{name}</span>
            {npc.title && <span className="npc-title-badge">{npc.title}</span>}
          </div>
          <div className="npc-usage-info">
            <span className="usage-count">{usages.length} quest(s)</span>
            <span className="expand-icon">{isExpanded ? '−' : '+'}</span>
          </div>
        </div>
        {isExpanded && (
          <div className="npc-card-body">
            <div className="npc-usages">
              <span className="usages-label">Used in:</span>
              {usages.map((usage, i) => (
                <span key={i} className="usage-badge">
                  [{usage.questId}] {usage.role}
                </span>
              ))}
            </div>

            <div className="form-section">
              <h4>Basic Info</h4>
              <div className="form-row">
                <div className="form-group">
                  <label>Name</label>
                  <input
                    type="text"
                    value={npc.name || ''}
                    onChange={(e) => updateNpcField(name, 'name', e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label>Title</label>
                  <input
                    type="text"
                    value={npc.title || ''}
                    onChange={(e) => updateNpcField(name, 'title', e.target.value)}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Personality</label>
                <textarea
                  value={npc.personality || ''}
                  onChange={(e) => updateNpcField(name, 'personality', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Lore</label>
                <textarea
                  value={npc.lore || ''}
                  onChange={(e) => updateNpcField(name, 'lore', e.target.value)}
                  rows={4}
                />
              </div>
            </div>

            <div className="form-section">
              {renderNpcLocationFields(name, npc.location)}
            </div>
          </div>
        )}
      </div>
    )
  }

  const renderNpcsTab = () => {
    const uniqueNpcs = getUniqueNpcs()
    if (uniqueNpcs.length === 0) {
      return <p className="no-data">No NPCs found in quests</p>
    }
    return (
      <div className="npcs-list">
        <p className="tab-description">
          Edit NPCs here to update all their occurrences across quests.
        </p>
        {uniqueNpcs.map((npcData, index) => renderNpcCard(npcData, index))}
      </div>
    )
  }

  return (
    <div className="validator-container">
      <div className="validator-header">
        <h1>Research Validator</h1>
        <div className="header-controls">
          {hasChanges && <span className="badge badge-warning">Unsaved Changes</span>}
          <select
            value={selectedSubject || ''}
            onChange={(e) => loadSubject(e.target.value)}
            disabled={loading}
          >
            {subjects.length === 0 ? (
              <option value="">No subjects available</option>
            ) : (
              subjects.map((subject) => (
                <option key={subject} value={subject}>{subject}</option>
              ))
            )}
          </select>
          <button
            onClick={handleSave}
            disabled={!hasChanges || saving || !researchData}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`message ${message.type}`}>
          <strong>{message.type}</strong>
          <div>{message.text}</div>
        </div>
      )}

      {loading ? (
        <div className="loading-message">Loading research data...</div>
      ) : researchData ? (
        <>
          <div className="validator-tabs">
            <button
              className={activeTab === 'setting' ? 'active' : ''}
              onClick={() => setActiveTab('setting')}
            >
              Setting
            </button>
            <button
              className={activeTab === 'npcs' ? 'active' : ''}
              onClick={() => setActiveTab('npcs')}
            >
              NPCs ({getUniqueNpcs().length})
            </button>
            <button
              className={activeTab === 'quests' ? 'active' : ''}
              onClick={() => setActiveTab('quests')}
            >
              Quests ({researchData.quests?.length || 0})
            </button>
            <button
              className={activeTab === 'roleplay' ? 'active' : ''}
              onClick={() => setActiveTab('roleplay')}
            >
              Roleplay
            </button>
          </div>

          <div className="validator-content">
            {activeTab === 'setting' && renderSettingTab()}
            {activeTab === 'npcs' && renderNpcsTab()}
            {activeTab === 'quests' && renderQuestsTab()}
            {activeTab === 'roleplay' && renderRoleplayTab()}
          </div>
        </>
      ) : (
        <div className="no-selection">Select a subject to validate</div>
      )}
    </div>
  )
}

export default ResearchValidator
