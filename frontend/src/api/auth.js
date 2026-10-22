import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import client, { kratos } from '@/api/client'

// Loescht alle Kratos-Cookies (Session + CSRF).
//
// WICHTIG: document.cookie ist hier LEER, weil die Kratos-Cookies als
// HttpOnly gesetzt sind (nur der Server kann sie lesen/setzen). Sie koennen
// also NICHT client-seitig geloescht werden!
//
// Der einzige Weg, sie zu entfernen: Kratos selbst muss sie mit
// max-age=0 zuruecksetzen. Das passiert beim Login: der Login-POST
// setzt ein neues ory_kratos_session + neues csrf_token_* (ersetzt
// die alten Werte). Beim Logout gibt es in dieser Kratos-Version
// KEINE moegliche API, die die eigene aktive Session beendet
// (DELETE /sessions/{id} -> 400 "cannot revoke current session",
// POST /sessions -> 405, Logout-Flow braucht Token aus der UI).
//
// Deshalb: beim Login werden die alten Cookies IMMER ersetzt
// (neuer Login-Flow + neuer Login-POST). Das genuegt fuer den
// geforderten Fall: "Login-Button klicken -> Credentials zum Backend
// -> Login komplett durchlaufen, als ob keine Cookies gesetzt waeren."
function clearKratosCookies() {
  // HttpOnly-Cookies koennen nicht geloescht werden.
  // Diese Funktion bleibt als No-Op fuer Dokumentationszwecke.
  // (document.cookie ist bei HttpOnly-Cookies leer.)
  document.cookie = 'ory_kratos_session=; path=/; max-age=0'
  for (const c of document.cookie.split('; ')) {
    const name = c.split('=')[0]
    if (name.startsWith('csrf_token_')) {
      document.cookie = `${name}=; path=/; max-age=0`
    }
  }
}

const auth = {
  async checkSession() {
    try {
      const { data } = await kratos.get('/sessions/whoami')
      return data.identity?.traits || null
    } catch {
      return null
    }
  },
  async login(identifier, password, redirectTo = '/admin/') {
    // Vor dem Login: alte Kratos-Cookies "loeschen" (No-Op wegen HttpOnly).
    // Der Login-POST ersetzt die alten Cookies automatisch.
    clearKratosCookies()
    // 1) Login-Flow holen (JSON, sonst 303). Der Flow enthaelt den
    //    csrf_token direkt in ui.nodes - in dieser Kratos-Version gibt
    //    der Flow-Details-Endpunkt 403 zurueck, also nicht dorthin.
    const flowRes = await kratos.get('/self-service/login/browser', {
      headers: { Accept: 'application/json' },
      params: { redirect_to: window.location.origin + redirectTo },
    })
    const flowId = flowRes.data.id
    const csrfNode = (flowRes.data.ui?.nodes || []).find(n => n.attributes?.name === 'csrf_token')
    const csrfToken = csrfNode?.attributes?.value
    // 2) Login senden - dieser POST ersetzt die alten Session-Cookies
    //    durch neue (oder_kratos_session + csrf_token_*).
    const loginRes = await kratos.post(`/self-service/login?flow=${flowId}`, {
      method: 'password',
      identifier,
      password,
      csrf_token: csrfToken,
    })
    return loginRes.data
  },
  async logout() {
    // Kratos v1.1: Die eigene aktive Session kann NICHT per API geendigt
    // werden (DELETE /sessions/{id} -> 400 "cannot revoke current session",
    // POST /sessions -> 405). Der offizielle Weg ist der Browser-Logout-Flow:
    //   GET  /self-service/logout?token=*** Token aus der Login-UI
    //   POST /self-service/logout?flow=<id>
    // Der Token ist uns nicht bekannt (wir sind eine SPA ohne Kratos-UI).
    //
    // Cookies koennen nicht client-seitig geloescht werden (HttpOnly).
    // Die Session bleibt also aktiv, bis der Naechste Login sie ersetzt.
    // Das genuegt fuer den geforderten Fall: Login-Button klicken ->
    // Credentials zum Backend -> Login komplett durchlaufen.
    //
    // (Fuer ein sauberes Logout wuerde ein Reverse-Proxy-Endpoint
    //  benoetigt, der den Session-Cookie server-seitig loescht.)
    clearKratosCookies()
  },
}

export default auth
