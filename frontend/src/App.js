import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// Context Providers
import { AuthProvider } from './context/AuthContext';
import { LanguageProvider } from './context/LanguageContext';
import { ConfettiProvider } from './context/ConfettiContext';
import { Web3Provider } from './context/Web3Context';

// Common Components
import Navbar from './components/common/Navbar';
import ProtectedRoute from './components/common/ProtectedRoute';
import DailyReward from './components/common/DailyReward';

// Pages
import {
  LandingPage,
  LoginPage,
  RegisterPage,
  DashboardPage,
  MetaversePage,
  JobsPage,
  CoursesPage,
  MarketplacePage,
  VotingPage,
  WalletPage,
  LeaderboardPage,
  ProfilePage,
  SimulationPage,
  ProjectsPage,
  ReferralPage
} from './pages';

// App Layout Component
const AppLayout = ({ children }) => (
  <div className="min-h-screen bg-black text-white scanlines noise">
    <Navbar />
    <DailyReward />
    {children}
  </div>
);

// Main App Component
function App() {
  return (
    <BrowserRouter>
      <LanguageProvider>
        <AuthProvider>
          <Web3Provider>
            <ConfettiProvider>
              <Routes>
                {/* Public Routes */}
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
              
              {/* Protected Routes */}
              <Route path="/dashboard" element={
                <ProtectedRoute>
                  <AppLayout>
                    <DashboardPage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              <Route path="/metaverse" element={
                <ProtectedRoute>
                  <AppLayout>
                    <MetaversePage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              <Route path="/jobs" element={
                <ProtectedRoute>
                  <AppLayout>
                    <JobsPage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              <Route path="/courses" element={
                <ProtectedRoute>
                  <AppLayout>
                    <CoursesPage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              <Route path="/marketplace" element={
                <ProtectedRoute>
                  <AppLayout>
                    <MarketplacePage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              <Route path="/voting" element={
                <ProtectedRoute>
                  <AppLayout>
                    <VotingPage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              <Route path="/wallet" element={
                <ProtectedRoute>
                  <AppLayout>
                    <WalletPage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              <Route path="/leaderboard" element={
                <ProtectedRoute>
                  <AppLayout>
                    <LeaderboardPage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              <Route path="/profile" element={
                <ProtectedRoute>
                  <AppLayout>
                    <ProfilePage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              <Route path="/simulation" element={
                <ProtectedRoute>
                  <AppLayout>
                    <SimulationPage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              <Route path="/projects" element={
                <ProtectedRoute>
                  <AppLayout>
                    <ProjectsPage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              <Route path="/referral" element={
                <ProtectedRoute>
                  <AppLayout>
                    <ReferralPage />
                  </AppLayout>
                </ProtectedRoute>
              } />
              
              {/* Catch all - redirect to dashboard */}
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
            </ConfettiProvider>
          </Web3Provider>
        </AuthProvider>
      </LanguageProvider>
    </BrowserRouter>
  );
}

export default App;
