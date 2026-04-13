import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
})

export const Chat = () => {
  const { token, user, logout } = useAuth()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [agentInfo, setAgentInfo] = useState(null)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Fetch agent info
    fetchAgentInfo()
  }, [])

  const fetchAgentInfo = async () => {
    try {
      const response = await api.get('/health', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setAgentInfo(response.data)
    } catch (error) {
      console.error('Failed to fetch agent info:', error)
    }
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage = input.trim()
    setInput('')
    
    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const response = await api.post(
        '/api/chat',
        {
          message: userMessage,
          contextId: `conv-${Date.now()}`,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      )

      const agentMessage = response.data.content || response.data.message || 'No response'
      setMessages(prev => [...prev, { role: 'assistant', content: agentMessage }])
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to get response'
      setMessages(prev => [...prev, { role: 'error', content: errorMsg }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">A2A Calculator Assistant</h1>
            <p className="text-sm text-gray-600">Logged in as {user?.email}</p>
          </div>
          <button
            onClick={logout}
            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Agent Info */}
      {agentInfo && (
        <div className="bg-blue-50 border-b border-blue-200 px-4 py-2 text-sm text-blue-800">
          Agent Status: {agentInfo.status} • Endpoint: {agentInfo.agent_url}
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 max-w-4xl mx-auto w-full overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="h-full flex items-center justify-center text-center">
            <div className="text-gray-400">
              <p className="text-lg mb-2">Welcome to A2A Calculator!</p>
              <p className="text-sm">Start by asking a math question like "What is 2 + 2?"</p>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-2 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : msg.role === 'error'
                  ? 'bg-red-100 text-red-800'
                  : 'bg-white text-gray-800 border border-gray-200'
              }`}
            >
              <p className="break-words">{msg.content}</p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white text-gray-800 border border-gray-200 px-4 py-2 rounded-lg">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 shadow">
        <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto px-4 py-4 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a math question..."
            disabled={loading}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 transition"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
