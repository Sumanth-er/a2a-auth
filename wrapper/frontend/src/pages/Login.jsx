import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

export const Login = () => {
  const { keycloak, loading } = useAuth()
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600">
        <div className="text-white text-xl">Loading...</div>
      </div>
    )
  }

  // Auto-redirect to chat if already authenticated
  if (keycloak?.authenticated) {
    navigate('/chat')
    return null
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-500 to-purple-600">
      <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">A2A ChatBot</h1>
          <p className="text-gray-600">Secure AI-powered Assistant</p>
        </div>
        
        <button
          onClick={() => keycloak?.login()}
          className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold py-3 rounded-lg hover:shadow-lg transition transform hover:scale-105"
        >
          Login with Keycloak
        </button>
        
        <p className="text-center text-gray-500 text-sm mt-6">
          Protected by Keycloak authentication
        </p>
      </div>
    </div>
  )
}
