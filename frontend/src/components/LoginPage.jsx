import { useState } from 'react'
import { login } from '../api/medorch'

const STAFF = [
  { user_id: 'user-001', name: 'Dr. Sarah Smith',  role: 'Clinician' },
  { user_id: 'user-002', name: 'Dr. James Patel',  role: 'Clinician' },
  { user_id: 'user-003', name: 'Dr. Aisha Nkosi',  role: 'Clinician' },
  { user_id: 'user-004', name: 'Mary Johnson',      role: 'Pharmacist' },
  { user_id: 'user-005', name: 'Tom Williams',      role: 'Operations Staff' },
  { user_id: 'admin-001',name: 'Admin',             role: 'Administrator' },
]

// ── SVG Illustrations ──────────────────────────────────────────────────────

function HospitalIllustration() {
  return (
    <svg viewBox="0 0 400 400" className="w-full max-w-md opacity-90">
      {/* Background circle */}
      <circle cx="200" cy="200" r="180" fill="#4A7C6F" opacity="0.08" />
      <circle cx="200" cy="200" r="140" fill="#4A7C6F" opacity="0.06" />

      {/* Hospital building */}
      <rect x="100" y="180" width="200" height="160" rx="4"
            fill="#4A7C6F" opacity="0.9" />
      <rect x="130" y="150" width="140" height="50" rx="4"
            fill="#3a6358" opacity="0.9" />
      <rect x="160" y="120" width="80" height="50" rx="4"
            fill="#2d4f46" opacity="0.9" />

      {/* Medical cross on building */}
      <rect x="183" y="195" width="34" height="10" rx="2" fill="white" opacity="0.95" />
      <rect x="195" y="183" width="10" height="34" rx="2" fill="white" opacity="0.95" />

      {/* Windows */}
      {[140,180,220,260].map(x => (
        <rect key={x} x={x} y="220" width="20" height="24" rx="3"
              fill="white" opacity="0.3" />
      ))}
      {[140,180,220,260].map(x => (
        <rect key={x+'b'} x={x} y="268" width="20" height="24" rx="3"
              fill="white" opacity="0.3" />
      ))}

      {/* Door */}
      <rect x="180" y="300" width="40" height="40" rx="3"
            fill="white" opacity="0.5" />

      {/* Heartbeat line */}
      <polyline
        points="40,280 70,280 85,240 100,320 115,260 130,280 360,280"
        fill="none" stroke="#6BAF9E" strokeWidth="2.5"
        strokeLinecap="round" strokeLinejoin="round" opacity="0.7" />

      {/* Floating icons */}
      {/* DNA helix dots */}
      {[0,1,2,3,4].map(i => (
        <g key={i}>
          <circle cx={50 + i*15} cy={80 + Math.sin(i) * 20}
                  r="4" fill="#6BAF9E" opacity="0.5" />
          <circle cx={55 + i*15} cy={100 + Math.cos(i) * 20}
                  r="4" fill="#4A7C6F" opacity="0.5" />
          <line x1={50 + i*15} y1={80 + Math.sin(i) * 20}
                x2={55 + i*15} y2={100 + Math.cos(i) * 20}
                stroke="#4A7C6F" strokeWidth="1" opacity="0.3" />
        </g>
      ))}

      {/* Pill icon top right */}
      <ellipse cx="340" cy="80" rx="28" ry="12"
               fill="#6BAF9E" opacity="0.4" transform="rotate(-45 340 80)" />
      <line x1="322" y1="62" x2="358" y2="98"
            stroke="white" strokeWidth="1.5" opacity="0.6" />

      {/* Stethoscope circle */}
      <circle cx="60" cy="180" r="18" fill="none"
              stroke="#4A7C6F" strokeWidth="2.5" opacity="0.4" />
      <line x1="60" y1="162" x2="60" y2="140"
            stroke="#4A7C6F" strokeWidth="2.5" opacity="0.4" />
      <circle cx="60" cy="136" r="5" fill="#4A7C6F" opacity="0.4" />

      {/* Circuit dots */}
      {[[340,160],[360,180],[330,200],[355,220]].map(([x,y],i) => (
        <circle key={i} cx={x} cy={y} r="3"
                fill="#6BAF9E" opacity="0.4" />
      ))}
      <polyline points="340,160 360,160 360,180 340,180 340,200 360,200 360,220"
                fill="none" stroke="#6BAF9E" strokeWidth="1"
                opacity="0.3" />
    </svg>
  )
}

function YCHealthLogo({ size = 'lg' }) {
  const big = size === 'lg'
  return (
    <div className={`flex items-center gap-3 ${big ? 'mb-2' : ''}`}>
      {/* Logo icon */}
      <div className={`${big ? 'w-12 h-12' : 'w-8 h-8'}
                       bg-brand-400 rounded-xl flex items-center
                       justify-center shadow-lg flex-shrink-0`}>
        <svg viewBox="0 0 32 32"
             className={big ? 'w-7 h-7' : 'w-5 h-5'}>
          <rect x="13" y="4"  width="6" height="24" rx="2" fill="white" />
          <rect x="4"  y="13" width="24" height="6"  rx="2" fill="white" />
        </svg>
      </div>
      <div>
        <h1 className={`${big ? 'text-3xl' : 'text-xl'}
                        font-bold text-brand-700 leading-none tracking-tight`}>
          YCHealth
        </h1>
        {big && (
          <p className="text-brand-300 text-sm font-medium tracking-widest uppercase mt-0.5">
            Intelligent Healthcare, Secured.
          </p>
        )}
      </div>
    </div>
  )
}

// ── Login Page ─────────────────────────────────────────────────────────────

export default function LoginPage({ onLogin }) {
  const [selectedUser, setSelectedUser] = useState(STAFF[0])
  const [password, setPassword]         = useState('')
  const [error, setError]               = useState('')
  const [loading, setLoading]           = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login(selectedUser.user_id, password)
      onLogin({
        user_id: res.data.user_id,
        name:    res.data.name,
        role:    res.data.role,
      })
    } catch {
      setError('Invalid password. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">

      {/* ── Left panel — illustration ── */}
      <div className="hidden lg:flex w-1/2 bg-gradient-to-br
                      from-brand-700 via-brand-500 to-brand-300
                      flex-col items-center justify-center p-12 relative overflow-hidden">

        {/* Background pattern */}
        <div className="absolute inset-0 opacity-10">
          {[...Array(8)].map((_, i) => (
            <div key={i}
                 className="absolute rounded-full border border-white"
                 style={{
                   width:  `${(i+1)*80}px`,
                   height: `${(i+1)*80}px`,
                   top:    '50%',
                   left:   '50%',
                   transform: 'translate(-50%, -50%)',
                 }} />
          ))}
        </div>

        <YCHealthLogo size="lg" />

        <div className="mt-8 w-full max-w-sm relative z-10">
          <HospitalIllustration />
        </div>

        <div className="mt-8 text-center relative z-10">
          <p className="text-white/80 text-sm max-w-xs leading-relaxed">
            Secure, role-aware AI orchestration for healthcare professionals.
            Powered by YCHealth.
          </p>
        </div>

        {/* Bottom disclaimer */}
        <p className="absolute bottom-6 text-white/40 text-xs text-center px-8">
          For demonstration purposes only. Not for clinical decision-making.
        </p>
      </div>

      {/* ── Right panel — login form ── */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <div className="w-full max-w-md">

          {/* Mobile logo */}
          <div className="lg:hidden mb-8 flex justify-center">
            <YCHealthLogo size="lg" />
          </div>

          <div className="bg-white rounded-2xl shadow-xl
                          border border-brand-100 p-8">

            <h2 className="text-2xl font-bold text-brand-700 mb-1">
              Welcome back
            </h2>
            <p className="text-brand-300 text-sm mb-8">
              Sign in to access the YCHealth AI Platform
            </p>

            <form onSubmit={handleLogin} className="space-y-5">

              {/* Staff selector */}
              <div>
                <label className="block text-sm font-semibold
                                   text-brand-600 mb-2">
                  Staff Member
                </label>
                <select
                  value={selectedUser.user_id}
                  onChange={e => {
                    const s = STAFF.find(s => s.user_id === e.target.value)
                    setSelectedUser(s)
                    setError('')
                  }}
                  className="w-full px-4 py-3 rounded-xl border border-brand-100
                             bg-surface text-brand-700 font-medium
                             focus:outline-none focus:ring-2
                             focus:ring-brand-300 focus:border-transparent
                             transition-all cursor-pointer"
                >
                  {STAFF.map(s => (
                    <option key={s.user_id} value={s.user_id}>
                      {s.name} — {s.role}
                    </option>
                  ))}
                </select>
              </div>

              {/* Role badge */}
              <div className="flex items-center gap-2 px-4 py-2.5
                              bg-brand-50 rounded-xl border border-brand-100">
                <div className="w-2 h-2 rounded-full bg-brand-400" />
                <span className="text-sm text-brand-600 font-medium">
                  Role: {selectedUser.role}
                </span>
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-semibold
                                   text-brand-600 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={e => { setPassword(e.target.value); setError('') }}
                  placeholder="Enter your password"
                  required
                  className="w-full px-4 py-3 rounded-xl border border-brand-100
                             bg-surface text-brand-700
                             focus:outline-none focus:ring-2
                             focus:ring-brand-300 focus:border-transparent
                             transition-all placeholder:text-brand-200"
                />
              </div>

              {/* Error */}
              {error && (
                <div className="flex items-center gap-2 px-4 py-3
                                bg-red-50 border border-red-200
                                rounded-xl text-red-600 text-sm">
                  <svg className="w-4 h-4 flex-shrink-0" fill="currentColor"
                       viewBox="0 0 20 20">
                    <path fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0
                         00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414
                         1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414
                         10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707
                         7.293z" clipRule="evenodd" />
                  </svg>
                  {error}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 bg-brand-400 hover:bg-brand-500
                           text-white font-semibold rounded-xl
                           transition-all duration-200 shadow-md
                           hover:shadow-lg disabled:opacity-60
                           disabled:cursor-not-allowed flex items-center
                           justify-center gap-2"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin w-5 h-5" fill="none"
                         viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10"
                              stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor"
                            d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Signing in...
                  </>
                ) : (
                  <>
                    Sign In
                    <svg className="w-5 h-5" fill="none" stroke="currentColor"
                         viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round"
                            strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </>
                )}
              </button>
            </form>

            {/* Hint */}
            <p className="mt-6 text-center text-xs text-brand-200">
              Clinicians: doctor123 · Pharmacists: pharma123 · Admin: admin2024
            </p>
          </div>

          <p className="mt-6 text-center text-xs text-brand-200">
            YCHealth AI Platform · Demo Environment · Not for clinical use
          </p>
        </div>
      </div>
    </div>
  )
}