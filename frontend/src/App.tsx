import { BrowserRouter, Routes, Route } from 'react-router-dom'
import CustomCursor from '@/components/layout/CustomCursor'
import Navbar from '@/components/layout/Navbar'
import HomePage from '@/pages/HomePage'
import AnalyserPage from '@/pages/AnalyserPage'
import LiveAnalysisPage from '@/pages/LiveAnalysisPage'
import ResultsPage from '@/pages/ResultsPage'

export default function App() {
  return (
    <BrowserRouter>
      <CustomCursor />
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/analyser" element={<AnalyserPage />} />
        <Route path="/analyze/live/:sessionId" element={<LiveAnalysisPage />} />
        <Route path="/results/:sessionId" element={<ResultsPage />} />
      </Routes>
    </BrowserRouter>
  )
}
