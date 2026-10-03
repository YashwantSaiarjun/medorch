import { useState, useRef, useEffect } from 'react'
import { chat } from '../api/medorch'

const PATIENT_IDS = Array.from({ length: 2000 }, (_, i) => `P${1001 + i}`)

const ROLE_CONFIG = {
  CLINICIAN:        { label: 'Clinician',        color: 'bg-blue-100 text-blue-700',    access: 'Diagnoses · Lab Results' },
  PHARMACIST:       { label: 'Pharmacist',        color: 'bg-purple-100 text-purple-700',access: 'Medications · Prescriptions' },
  OPERATIONS_STAFF: { label: 'Operations Staff',  color: 'bg-amber-100 text-amber-700',  access: 'Appointments · Admissions' },
}

function Logo() {
  return (
    <div className="flex items-center gap-2">
      <div className="w-8 h-8 bg-brand-400 rounded-lg flex items-center justify-center">
        <svg viewBox="0 0 32 32" className="w-5 h-5">
          <rect x="13" y="4"  width="6" height="24" rx="2" fill="white" />
          <rect x="4"  y="13" width="24" height="6"  rx="2" fill="white" />
        </svg>
      </div>
      <span className="font-bold text-brand-700 text-lg tracking-tight">NexaCare</span>
    </div>
  )
}

function StatusBadge({ status }) {
  const config = {
    ALLOWED:        { cls: 'bg-green-100 text-green-700',   icon: '✅', label: 'Authorized' },
    PARTIAL:        { cls: 'bg-yellow-100 text-yellow-700', icon: '⚠️', label: 'Partial Access' },
    DENIED:         { cls: 'bg-red-100 text-red-700',       icon: '🚫', label: 'Access Denied' },
    PATIENT_DENIED: { cls: 'bg-red-100 text-red-700',       icon: '🔒', label: 'Patient Restricted' },
    NEEDS_ROLE:     { cls: 'bg-gray-100 text-gray-700',     icon: 'ℹ️', label: 'Role Required' },
  }[status] || { cls: 'bg-gray-100 text-gray-600', icon: '?', label: status }

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${config.cls}`}>
      <span>{config.icon}</span>
      {config.label}
    </span>
  )
}

function ChatMessage({ turn }) {
  const [showSources, setShowSources] = useState(false)
  const isDenied = ['DENIED', 'PATIENT_DENIED', 'NEEDS_ROLE'].includes(turn.status)

  return (
    <div className="space-y-3">
      {/* User message */}
      <div className="flex justify-end">
        <div className="max-w-lg bg-brand-400 text-white px-4 py-3 rounded-2xl rounded-tr-sm shadow-sm">
          <p className="text-sm">{turn.request}</p>
        </div>
      </div>

      {/* AI response */}
      <div className="flex justify-start">
        <div className="max-w-2xl w-full">
          <div className="bg-white border border-brand-100 rounded-2xl rounded-tl-sm shadow-sm overflow-hidden">

            {/* Meta bar */}
            <div className="px-4 py-3 bg-brand-50 border-b border-brand-100 flex flex-wrap gap-2 items-center">
              <StatusBadge status={turn.status} />

              {turn.agents_considered?.length > 0 && (
                <span className="text-xs text-brand-400 font-medium">
                  🔍 {turn.agents_considered.join(', ')}
                </span>
              )}

              {turn.tools_called?.length > 0 && (
                <span className="text-xs text-brand-400 font-medium">
                  🔧 {turn.tools_called.join(', ')}
                </span>
              )}

              {turn.denied_agents?.length > 0 && (
                <span className="text-xs text-red-400 font-medium">
                  🚫 denied: {turn.denied_agents.join(', ')}
                </span>
              )}
            </div>

            {/* Answer */}
            <div className="px-4 py-4">
              {isDenied ? (
                <div className="flex items-start gap-3 text-red-600">
                  <span className="text-lg mt-0.5">🔒</span>
                  <p className="text-sm leading-relaxed">{turn.final_response}</p>
                </div>
              ) : (
                <p className="text-sm text-brand-700 leading-relaxed whitespace-pre-wrap">
                  {turn.final_response}
                </p>
              )}
            </div>

            {/* Sources */}
            {turn.citations?.length > 0 && (
              <div className="px-4 pb-4">
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="text-xs text-brand-300 hover:text-brand-400
                             font-medium flex items-center gap-1 transition-colors"
                >
                  📚 {showSources ? 'Hide' : 'Show'} sources ({turn.citations.length})
                </button>
                {showSources && (
                  <div className="mt-2 space-y-1">
                    {turn.citations.map((c, i) => (
                      <div key={i} className="text-xs text-brand-400 bg-brand-50
                                              px-3 py-2 rounded-lg flex items-center gap-2">
                        <span className="font-mono text-brand-300">{c.doc_id}</span>
                        <span>{c.title}</span>
                        <span className="ml-auto text-brand-200">{c.score?.toFixed(3)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ChatPage({ session, onLogout }) {
  const [patientId, setPatientId]   = useState('')
  const [message, setMessage]       = useState('')
  const [history, setHistory]       = useState([])
  const [loading, setLoading]       = useState(false)
  const bottomRef                   = useRef(null)
  const roleConfig                  = ROLE_CONFIG[session.role] || {}

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!message.trim()) return
    if (!patientId) {
      alert('Please select a patient first.')
      return
    }

    const userMessage = message.trim()
    setMessage('')
    setLoading(true)

    try {
      const res = await chat({
        user_id:    session.user_id,
        role:       session.role,
        patient_id: patientId,
        message:    userMessage,
      })
      setHistory(h => [...h, {
        request:          userMessage,
        agents_considered:res.data.agents_considered || [],
        status:           res.data.status,
        denied_agents:    res.data.denied_agents || [],
        executed_agents:  res.data.executed_agents || [],
        tools_called:     res.data.tools_called || [],
        final_response:   res.data.final_response || '',
        citations:        res.data.citations || [],
      }])
    } catch (err) {
      setHistory(h => [...h, {
        request:       userMessage,
        status:        'ERROR',
        final_response:`Error: ${err.response?.data?.detail || err.message}`,
        citations:     [],
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-surface">

      {/* ── Header ── */}
      <header className="bg-white border-b border-brand-100 px-6 py-4
                         flex items-center justify-between shadow-sm flex-shrink-0">
        <Logo />

        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-semibold text-brand-700">{session.name}</p>
            <p className="text-xs text-brand-300">{roleConfig.label}</p>
          </div>
          <div className={`px-3 py-1 rounded-full text-xs font-semibold ${roleConfig.color}`}>
            {roleConfig.label}
          </div>
          <button
            onClick={onLogout}
            className="px-4 py-2 text-sm text-brand-400 hover:text-brand-600
                       border border-brand-200 hover:border-brand-400
                       rounded-xl transition-all font-medium"
          >
            Logout
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">

        {/* ── Sidebar ── */}
        <aside className="w-72 bg-white border-r border-brand-100
                          flex flex-col flex-shrink-0 overflow-y-auto">
          <div className="p-5 space-y-5">

            {/* Staff info */}
            <div className="bg-brand-50 rounded-xl p-4 border border-brand-100">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-brand-400 rounded-full
                                flex items-center justify-center text-white
                                font-bold text-sm flex-shrink-0">
                  {session.name.split(' ').map(n => n[0]).join('').slice(0,2)}
                </div>
                <div>
                  <p className="font-semibold text-brand-700 text-sm leading-tight">
                    {session.name}
                  </p>
                  <p className="text-xs text-brand-300">{roleConfig.label}</p>
                </div>
              </div>
              <div className="text-xs text-brand-400 bg-white rounded-lg
                              px-3 py-2 border border-brand-100">
                <span className="font-semibold">Access: </span>
                {roleConfig.access}
              </div>
            </div>

            {/* Patient selector */}
            <div>
              <label className="block text-xs font-semibold text-brand-600 mb-2 uppercase tracking-wider">
                Select Patient
              </label>
              <select
                value={patientId}
                onChange={e => setPatientId(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border border-brand-100
                           bg-surface text-brand-700 text-sm font-medium
                           focus:outline-none focus:ring-2 focus:ring-brand-300
                           cursor-pointer"
              >
                <option value="">-- Select a patient --</option>
                {PATIENT_IDS.map(id => (
                  <option key={id} value={id}>{id}</option>
                ))}
              </select>
            </div>

            {/* Active patient card */}
            {patientId && (
              <div className="bg-brand-400 rounded-xl p-4 text-white">
                <p className="text-xs opacity-75 mb-1">Active Patient</p>
                <p className="font-bold text-lg">{patientId}</p>
                <div className="mt-2 pt-2 border-t border-white/20">
                  <p className="text-xs opacity-75">
                    {roleConfig.access}
                  </p>
                </div>
              </div>
            )}

            {/* Access matrix */}
            <div>
              <p className="text-xs font-semibold text-brand-600 mb-2 uppercase tracking-wider">
                Security Model
              </p>
              <div className="space-y-1.5 text-xs">
                {[
                  { role: 'Clinician',  access: 'Diagnoses, Labs',      color: 'bg-blue-100 text-blue-600' },
                  { role: 'Pharmacist', access: 'Medications, Rx',      color: 'bg-purple-100 text-purple-600' },
                  { role: 'Operations', access: 'Appointments, Admits', color: 'bg-amber-100 text-amber-600' },
                ].map(r => (
                  <div key={r.role} className={`px-3 py-2 rounded-lg ${r.color} flex justify-between`}>
                    <span className="font-medium">{r.role}</span>
                    <span className="opacity-75">{r.access}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Clear chat */}
            <button
              onClick={() => setHistory([])}
              className="w-full py-2 text-xs text-brand-300 hover:text-brand-500
                         border border-brand-100 hover:border-brand-300
                         rounded-xl transition-all font-medium"
            >
              Clear conversation
            </button>
          </div>
        </aside>

        {/* ── Chat area ── */}
        <main className="flex-1 flex flex-col overflow-hidden">

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            {history.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <div className="w-16 h-16 bg-brand-50 rounded-2xl
                                flex items-center justify-center mb-4 border border-brand-100">
                  <svg viewBox="0 0 32 32" className="w-8 h-8">
                    <rect x="13" y="4"  width="6" height="24" rx="2" fill="#4A7C6F" />
                    <rect x="4"  y="13" width="24" height="6"  rx="2" fill="#4A7C6F" />
                  </svg>
                </div>
                <h3 className="text-brand-700 font-semibold mb-1">
                  NexaCare AI Assistant
                </h3>
                <p className="text-brand-300 text-sm max-w-sm">
                  {patientId
                    ? `Select a question to ask about patient ${patientId}`
                    : 'Select a patient from the sidebar to begin'}
                </p>

                {patientId && (
                  <div className="mt-6 grid grid-cols-1 gap-2 w-full max-w-md">
                    {[
                      'Show diagnosis and lab results',
                      'What medications is this patient on?',
                      'Show appointments and admission status',
                      'What is hypertension?',
                    ].map(q => (
                      <button
                        key={q}
                        onClick={() => setMessage(q)}
                        className="px-4 py-2.5 text-sm text-brand-600 bg-white
                                   border border-brand-100 rounded-xl
                                   hover:border-brand-300 hover:bg-brand-50
                                   transition-all text-left font-medium"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {history.map((turn, i) => (
              <ChatMessage key={i} turn={turn} />
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-white border border-brand-100 rounded-2xl
                                px-4 py-3 shadow-sm">
                  <div className="flex items-center gap-2 text-brand-300">
                    <div className="flex gap-1">
                      {[0,1,2].map(i => (
                        <div key={i}
                             className="w-2 h-2 bg-brand-300 rounded-full animate-bounce"
                             style={{ animationDelay: `${i*0.15}s` }} />
                      ))}
                    </div>
                    <span className="text-xs">Processing...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* ── Input bar ── */}
          <div className="border-t border-brand-100 bg-white px-6 py-4 flex-shrink-0">
            <form onSubmit={handleSend} className="flex gap-3">
              <input
                value={message}
                onChange={e => setMessage(e.target.value)}
                placeholder={patientId
                  ? `Ask about patient ${patientId}...`
                  : 'Select a patient first...'}
                disabled={!patientId || loading}
                className="flex-1 px-4 py-3 rounded-xl border border-brand-100
                           bg-surface text-brand-700 text-sm
                           focus:outline-none focus:ring-2 focus:ring-brand-300
                           placeholder:text-brand-200 disabled:opacity-50
                           disabled:cursor-not-allowed transition-all"
              />
              <button
                type="submit"
                disabled={!message.trim() || !patientId || loading}
                className="px-5 py-3 bg-brand-400 hover:bg-brand-500
                           text-white rounded-xl font-semibold text-sm
                           transition-all shadow-md hover:shadow-lg
                           disabled:opacity-50 disabled:cursor-not-allowed
                           flex items-center gap-2"
              >
                {loading ? (
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10"
                            stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                )}
                Send
              </button>
            </form>
            <p className="mt-2 text-xs text-brand-200 text-center">
              NexaCare AI · Demo only · Not for clinical decision-making
            </p>
          </div>
        </main>
      </div>
    </div>
  )
}