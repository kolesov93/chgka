import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { entrypointDocumentTitle, resolveEntrypoint } from './entrypoint.js'
import './index.css'

const { entrypoint, canonicalPath } = resolveEntrypoint(window.location.pathname)
document.title = entrypointDocumentTitle(entrypoint)
if (window.location.pathname !== canonicalPath) {
  window.history.replaceState(
    window.history.state,
    '',
    `${canonicalPath}${window.location.search}${window.location.hash}`,
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App entrypoint={entrypoint} />
  </React.StrictMode>,
)
