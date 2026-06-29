import { useRef, useState } from 'react'
import { uploadDocument } from '../api.js'

export default function DocumentUpload({ token }) {
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const inputRef = useRef(null)

  async function onChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy(true)
    setStatus(`"${file.name}" yükleniyor…`)
    try {
      const result = await uploadDocument(file, token)
      setStatus(`✓ "${file.name}" yüklendi (${result.chunks} parça). Artık içeriğinden sorabilirsin.`)
    } catch (err) {
      setStatus('✗ ' + err.message)
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="upload">
      <label className="upload-btn">
        {busy ? 'Yükleniyor…' : '📄 PDF yükle'}
        <input ref={inputRef} type="file" accept="application/pdf,.pdf" onChange={onChange} disabled={busy} hidden />
      </label>
      {status && <span className="upload-status">{status}</span>}
    </div>
  )
}
