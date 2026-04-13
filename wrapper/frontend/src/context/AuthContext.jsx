import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import Keycloak from 'keycloak-js'

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
  const [keycloak, setKeycloak] = useState(null)
  const [authenticated, setAuthenticated] = useState(false)
  const [token, setToken] = useState(null)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const initKeycloak = async () => {
      const kc = new Keycloak({
        url: import.meta.env.VITE_KEYCLOAK_URL,
        realm: import.meta.env.VITE_KEYCLOAK_REALM,
        clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
      })

      try {
        const authenticated = await kc.init({
          onLoad: 'login-required',
          flow: 'standard',
          promiseType: 'native',
        })

        setKeycloak(kc)
        setAuthenticated(authenticated)
        
        if (authenticated) {
          setToken(kc.token)
          setUser(kc.idTokenParsed)
          
          // Auto-refresh token
          setInterval(() => {
            kc.updateToken(70).catch(() => kc.logout())
          }, 60000) // Check every minute
        }
      } catch (error) {
        console.error('Keycloak init failed:', error)
      } finally {
        setLoading(false)
      }
    }

    initKeycloak()
  }, [])

  const logout = useCallback(() => {
    keycloak?.logout()
  }, [keycloak])

  return (
    <AuthContext.Provider value={{ keycloak, authenticated, token, user, loading, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
