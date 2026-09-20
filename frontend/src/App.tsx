import { Routes, Route, Navigate } from 'react-router-dom'
import { useState } from 'react'
import Navbar from './components/Navbar'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import Connections from './pages/Connections'
import Expenses from './pages/Expenses'
import Reports from './pages/Reports'

function App() {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('meraki_token')
  )

  const isLoggedIn = !!token

  const handleLogin = (newToken: string) => {
    localStorage.setItem('meraki_token', newToken)
    setToken(newToken)
  }

  const handleLogout = () => {
    localStorage.removeItem('meraki_token')
    setToken(null)
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar isLoggedIn={isLoggedIn} onLogout={handleLogout} />
      <main className="max-w-5xl mx-auto px-4 py-8 w-full flex-1">
        <Routes>
          <Route path="/" element={isLoggedIn ? <Navigate to="/dashboard" /> : <Landing />} />
          <Route path="/login" element={isLoggedIn ? <Navigate to="/dashboard" /> : <Login onLogin={handleLogin} />} />
          <Route path="/signup" element={isLoggedIn ? <Navigate to="/dashboard" /> : <Signup onLogin={handleLogin} />} />
          <Route path="/dashboard" element={isLoggedIn ? <Dashboard /> : <Navigate to="/login" />} />
          <Route path="/connections" element={isLoggedIn ? <Connections /> : <Navigate to="/login" />} />
          <Route path="/settings/connections" element={<Navigate to="/connections" replace />} />
          <Route path="/expenses" element={isLoggedIn ? <Expenses /> : <Navigate to="/login" />} />
          <Route path="/reports" element={isLoggedIn ? <Reports /> : <Navigate to="/login" />} />
        </Routes>
      </main>
      <footer className="text-xs text-gray-400 text-center py-6">
        Tax calculations are estimates. Consult your accountant.
      </footer>
    </div>
  )
}

export default App
