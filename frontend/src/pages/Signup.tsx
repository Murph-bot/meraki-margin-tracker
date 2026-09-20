import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiClient } from '../api/client'

export default function Signup({ onLogin }: { onLogin: (token: string) => void }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const res = await apiClient.post('/auth/signup', { name, email, password })
      onLogin(res.data.token)
      navigate('/dashboard')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setError(detail || 'Signup failed')
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16">
      <h1 className="text-2xl font-bold mb-6">Create your Meraki account</h1>
      {error && <p className="text-red-600 mb-4" role="alert">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <input type="text" placeholder="Full name" value={name}
          onChange={e => setName(e.target.value)}
          className="w-full border rounded px-3 py-2" required aria-label="Full name" />
        <input type="email" placeholder="Email" value={email}
          onChange={e => setEmail(e.target.value)}
          className="w-full border rounded px-3 py-2" required aria-label="Email" />
        <input type="password" placeholder="Password (min 8 characters)" value={password}
          onChange={e => setPassword(e.target.value)}
          className="w-full border rounded px-3 py-2" required minLength={8} aria-label="Password" />
        <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
          Sign up
        </button>
      </form>
      <p className="mt-4 text-sm">Already have an account? <Link to="/login" className="text-blue-600">Log in</Link></p>
    </div>
  )
}
