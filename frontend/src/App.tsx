import { UploadPage } from './pages/UploadPage'

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__inner">
          <span className="app-header__icon" aria-hidden="true">🏊</span>
          <h1 className="app-header__title">AI Swim Coach</h1>
        </div>
      </header>
      <main className="app-main">
        <UploadPage />
      </main>
    </div>
  )
}

export default App
