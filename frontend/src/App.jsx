import { useState } from 'react'
import Login from './components/Login.jsx'
import Chat from './components/Chat.jsx'

const TOKEN_KEY = 'chatbot_jwt'

export default function App() {
  // JWT'yi localStorage'da tutuyoruz: yenilemede oturum kalsın (UX).
  // Trade-off: XSS varsa token okunabilir. Demo için kabul; üretimde httpOnly cookie düşünülür.
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '')

  function handleAuth(newToken) {
    localStorage.setItem(TOKEN_KEY, newToken)
    setToken(newToken)
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('chatbot_conversation_id')
    setToken('')
  }

  if (!token) return <Login onAuth={handleAuth} />
  return <Chat token={token} onLogout={logout} />
}
