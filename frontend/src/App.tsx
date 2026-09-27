import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomeScreen from './components/HomeScreen';
import AnalysisResultsScreen from './components/AnalysisResultsScreen';
import './app-styles.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<HomeScreen />} />
          <Route path="/results" element={<AnalysisResultsScreen />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
