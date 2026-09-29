import { useEffect, useState } from 'react'
import { api } from './api'
import { Accueil } from './pages/Accueil'
import { Parcours } from './pages/Parcours'

// Navigation minimale par le fragment d'URL : #/session/<id>
function sessionDepuisUrl() {
  return /^#\/session\/(\w+)/.exec(window.location.hash)?.[1] ?? null
}

function App() {
  const [sessionId, setSessionId] = useState<string | null>(sessionDepuisUrl)
  const [horsLigne, setHorsLigne] = useState(false)

  useEffect(() => {
    api.sante().then((s) => setHorsLigne(s.demo)).catch(() => undefined)
    const surChangement = () => setSessionId(sessionDepuisUrl())
    window.addEventListener('hashchange', surChangement)
    return () => window.removeEventListener('hashchange', surChangement)
  }, [])

  const ouvrir = (id: string | null) => {
    window.location.hash = id ? `/session/${id}` : ''
    setSessionId(id)
  }

  return sessionId ? (
    <Parcours key={sessionId} sessionId={sessionId} horsLigne={horsLigne} onAccueil={() => ouvrir(null)} />
  ) : (
    <Accueil horsLigne={horsLigne} onOuvrir={ouvrir} />
  )
}

export default App
