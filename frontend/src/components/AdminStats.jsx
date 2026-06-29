import { useEffect, useState } from 'react'
import { getAdminStats } from '../api.js'

export default function AdminStats({ token }) {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    getAdminStats(token)
      .then((data) => !cancelled && setStats(data))
      .catch((err) => !cancelled && setError(err.message))
    return () => {
      cancelled = true
    }
  }, [token])

  if (error) return <main className="admin"><p className="error">{error}</p></main>
  if (!stats) return <main className="admin"><p>Yükleniyor…</p></main>

  return (
    <main className="admin">
      <h2>Admin İstatistikleri</h2>
      <table>
        <tbody>
          <tr><td>Aktif bağlantı</td><td>{stats.active_connections}</td></tr>
          <tr><td>Toplam mesaj</td><td>{stats.total_messages}</td></tr>
        </tbody>
      </table>
    </main>
  )
}
