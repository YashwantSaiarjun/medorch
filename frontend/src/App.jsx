import { useState } from 'react'
import LoginPage from './components/LoginPage'
import ChatPage from './components/ChatPage'

export default function App() {
  const [session, setSession] = useState(null)

  const handleLogin = (sessionData) => {
    setSession(sessionData)
  }

  const handleLogout = () => {
    setSession(null)
  }

  return (
    <div className="min-h-screen bg-surface">
      {!session
        ? <LoginPage onLogin={handleLogin} />
        : <ChatPage session={session} onLogout={handleLogout} />
      }
    </div>
  )
}