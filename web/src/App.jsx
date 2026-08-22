import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Public from './pages/Public'
import Correspondant from './pages/Correspondant'
import Admin from './pages/Admin'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Public />} />
        <Route path="/correspondant/:matchId" element={<Correspondant />} />
        <Route path="/admin" element={<Admin />} />
      </Routes>
    </BrowserRouter>
  )
}
