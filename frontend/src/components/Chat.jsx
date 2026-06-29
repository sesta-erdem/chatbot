import { useEffect, useRef, useState } from 'react'
import { wsUrl } from '../api.js'
import DocumentUpload from './DocumentUpload.jsx'
import AdminStats from './AdminStats.jsx'

const CONV_KEY = 'chatbot_conversation_id'

const STATUS_LABEL = {
  connecting: 'bağlanıyor…',
  connected: 'bağlandı',
  disconnected: 'bağlantı kesildi',
  'auth-error': 'oturum geçersiz — çıkış yapıp tekrar gir',
}

export default function Chat({ token, onLogout }) {
  const [messages, setMessages] = useState([]) // {role, text, sources?, error?}
  const [status, setStatus] = useState('connecting')
  const [input, setInput] = useState('')
  const [showAdmin, setShowAdmin] = useState(false)
  const wsRef = useRef(null)
  const streamingRef = useRef(false)
  const endRef = useRef(null)

  // WebSocket'i token'a bağlı bir effect'te kur; cleanup'ta KAPAT.
  // Cleanup olmazsa StrictMode'un çift-mount'u + route değişimi bağlantı sızdırır.
  useEffect(() => {
    const conversationId = localStorage.getItem(CONV_KEY) || null
    const ws = new WebSocket(wsUrl(token, conversationId))
    wsRef.current = ws

    ws.onopen = () => setStatus('connected')
    ws.onerror = () => setStatus('disconnected')
    ws.onclose = (e) => setStatus(e.code === 1008 ? 'auth-error' : 'disconnected')

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)

      if (msg.type === 'conversation') {
        localStorage.setItem(CONV_KEY, msg.conversation_id)
        return
      }

      if (msg.type === 'chunk') {
        setMessages((prev) => {
          const copy = [...prev]
          if (!streamingRef.current) {
            copy.push({ role: 'assistant', text: '' })
            streamingRef.current = true
          }
          const last = copy[copy.length - 1]
          copy[copy.length - 1] = { ...last, text: last.text + msg.content }
          return copy
        })
      } else if (msg.type === 'done') {
        setMessages((prev) => {
          const copy = [...prev]
          const last = copy[copy.length - 1]
          if (last && last.role === 'assistant') {
            copy[copy.length - 1] = { ...last, sources: msg.sources || [] }
          }
          return copy
        })
        streamingRef.current = false
      } else if (msg.type === 'error' || msg.type === 'system') {
        streamingRef.current = false
        setMessages((prev) => [...prev, { role: 'assistant', text: msg.content, error: true }])
      }
    }

    return () => ws.close()
  }, [token])

  // Yeni mesajda en alta kaydır
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function send() {
    const text = input.trim()
    if (!text || wsRef.current?.readyState !== WebSocket.OPEN) return
    setMessages((prev) => [...prev, { role: 'user', text }])
    wsRef.current.send(JSON.stringify({ type: 'user_message', content: text }))
    setInput('')
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <strong>Gemini Chatbot</strong>
        <span className={'status ' + status}>{STATUS_LABEL[status]}</span>
        <div className="spacer" />
        <button className="link" onClick={() => setShowAdmin((s) => !s)}>
          {showAdmin ? 'Sohbet' : 'Admin'}
        </button>
        <button className="link" onClick={onLogout}>Çıkış</button>
      </header>

      {showAdmin ? (
        <AdminStats token={token} />
      ) : (
        <main className="chat">
          <div className="feed">
            {messages.length === 0 && <p className="empty">Bir şey sor ya da bir PDF yükle.</p>}
            {messages.map((m, i) => (
              <div key={i} className={'bubble ' + m.role + (m.error ? ' error' : '')}>
                <div className="text">{m.text}</div>
                {m.sources && m.sources.length > 0 && (
                  <div className="sources">
                    {m.sources.map((s, j) => (
                      <span key={j} className="source-badge">
                        {s.file}{s.page != null ? ` · s.${s.page}` : ''}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div ref={endRef} />
          </div>

          <DocumentUpload token={token} />

          <div className="composer">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Mesaj yaz… (Enter gönder, Shift+Enter satır)"
              rows={2}
            />
            <button onClick={send} disabled={status !== 'connected'}>Gönder</button>
          </div>
        </main>
      )}
    </div>
  )
}
