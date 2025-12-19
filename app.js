let cid = localStorage.getItem('cid') || ''
if (!cid) {
  cid = Math.random().toString(36).slice(2)
  localStorage.setItem('cid', cid)
}
const messages = document.getElementById('messages')
const input = document.getElementById('input')
const send = document.getElementById('send')
function add(role, text) {
  const d = document.createElement('div')
  d.className = 'msg ' + role
  const b = document.createElement('div')
  b.className = 'bubble'
  b.textContent = text
  d.appendChild(b)
  messages.appendChild(d)
  messages.scrollTop = messages.scrollHeight
}
function addSuggestions(items) {
  if (!items || !items.length) return
  const c = document.createElement('div')
  c.className = 'suggestions'
  items.forEach(x => {
    const s = document.createElement('div')
    s.className = 'suggestion'
    s.textContent = x
    s.onclick = () => {
      input.value = x
      send.click()
    }
    c.appendChild(s)
  })
  messages.appendChild(c)
  messages.scrollTop = messages.scrollHeight
}
async function ask(text) {
  add('user', text)
  input.value = ''
  const r = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, conversationId: cid }) })
  const j = await r.json()
  add('bot', j.reply + (j.handoff ? ' You can contact a human at support@example.com.' : ''))
  addSuggestions(j.suggestions)
}
send.onclick = () => {
  const v = input.value.trim()
  if (!v) return
  ask(v)
}
input.addEventListener('keydown', e => {
  if (e.key === 'Enter') send.click()
})
add('bot', 'Hello. Ask a question or pick a suggested topic.')
fetch('/api/faqs').then(r => r.json()).then(xs => {
  const items = xs.map(x => x.question)
  addSuggestions(items.slice(0, 6))
})
