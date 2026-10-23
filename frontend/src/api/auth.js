import client, { kratos } from '@/api/client'

/**
 * Erzwingt serverseitig den Abbruch der aktiven Kratos-Session.
 *
 * Hintergrund: Kratos v1.1 erlaubt es nicht, die eigene aktive Session
 * per API zu beenden (DELETE /sessions/{id} -> 400 "cannot revoke
 * current session"). Außerdem ist der Session-Cookie HttpOnly und kann
 * nicht clientseitig geloescht werden.
 *
 * Loesung: nginx hat einen Endpoint GET /logout, der den Cookie
 * serverseitig mit Max-Age=0 zuruecksetzt. Der Cookie hat KEIN
 * Domain-Attribut, daher reicht ein plain fetch (redirect: 'manual')
 * aus derselben Origin, um ihn zu ersetzen.
 *
 * Der Query-Parameter `token` ist der Pfad, zu dem nginx danach
 * redirectet (302) - bei uns immer die Login-Seite.
 *
 * WICHTIG: Danach muss der Login-Flow NEU gestartet werden, da der
 * CSRF-Token des alten Flows mit der Session gueltig war.
 */
async function forceLogout(redirectTo = '/admin/login') {
  await fetch('/logout?token=' + encodeURIComponent(redirectTo), {
    method: 'GET',
    redirect: 'manual',
  })
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

  /**
   * Login: setzt die Session NEU, egal ob vorher eine existierte.
   *
   * Ablauf:
   *  1) forceLogout -> alte Session-Cookies werden serverseitig
   *     mit Max-Age=0 zurueckgesetzt. Danach ist der Werami-Status
   *     garantiert 401, und der Login-Flow-GET liefert keinen
   *     Redirect, sondern einen frischen Flow.
   *  2) Login-Flow holen (JSON).
   *  3) Login senden (POST). Der POST setzt frische
   *     ory_kratos_session + csrf_token_* Cookies.
   */
  async login(identifier, password, redirectTo = '/admin/') {
    // 1) Alte Session serverseitig abbrechen.
    //    Ohne diesen Schritt: Wenn eine Session existiert, leitet
    //    Kratos den Login-Flow-GET um (303) und axios bekommt HTML
    //    statt JSON -> flow.id fehlt -> POST 400.
    await forceLogout(redirectTo)

    // 2) Frischen Login-Flow holen (JSON).
    const flowRes = await kratos.get('/self-service/login/browser', {
      headers: { Accept: 'application/json' },
      params: { redirect_to: window.location.origin + redirectTo },
    })
    const flowId = flowRes.data.id
    const csrfNode = (flowRes.data.ui?.nodes || []).find(n => n.attributes?.name === 'csrf_token')
    const csrfToken = csrfNode?.attributes?.value

    // 3) Login senden. Setzt frische Session-Cookies.
    const loginRes = await kratos.post(`/self-service/login?flow=${flowId}`, {
      method: 'password',
      identifier,
      password,
      csrf_token: csrfToken,
    })
    return loginRes.data
  },

  /**
   * Logout: serverseitig Session-Cookie loeschen.
   * Kein Redirect - die SPA uebernimmt die Navigation.
   */
  async logout(redirectTo = '/admin/login') {
    await forceLogout(redirectTo)
  },
}

export default auth
