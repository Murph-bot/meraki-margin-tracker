import { Link } from 'react-router-dom'

export default function Navbar({ isLoggedIn, onLogout }: { isLoggedIn: boolean; onLogout: () => void }) {
  return (
    <nav className="bg-white border-b shadow-sm">
      <div className="max-w-5xl mx-auto px-4 py-3 flex justify-between items-center">
        <Link to="/" className="text-xl font-bold text-blue-600">Meraki</Link>
        <div className="flex gap-4 items-center">
          {isLoggedIn ? (
            <>
              <Link to="/dashboard" className="text-sm hover:text-blue-600">Dashboard</Link>
              <Link to="/connections" className="text-sm hover:text-blue-600">Connections</Link>
              <Link to="/expenses" className="text-sm hover:text-blue-600">Expenses</Link>
              <Link to="/reports" className="text-sm hover:text-blue-600">Reports</Link>
              <button type="button" onClick={onLogout} className="text-sm text-gray-500 hover:text-red-600" aria-label="Log out">Logout</button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm hover:text-blue-600">Log in</Link>
              <Link to="/signup" className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700">Sign up</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
