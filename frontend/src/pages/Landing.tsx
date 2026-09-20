import { Link } from 'react-router-dom'

export default function Landing() {
  return (
    <div className="text-center mt-24">
      <h1 className="text-5xl font-bold mb-4">Μεράκι</h1>
      <p className="text-xl text-gray-600 mb-2">Your true take-home. Finally.</p>
      <p className="text-gray-500 mb-8 max-w-lg mx-auto">
        Connect your payment processor and see exactly what you keep after Stripe fees,
        income tax, social security, and expenses.
      </p>
      <Link to="/signup" className="bg-blue-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-blue-700">
        Start for free
      </Link>
      <p className="text-xs text-gray-400 mt-2">No credit card needed &bull; 2-minute setup</p>
    </div>
  )
}
