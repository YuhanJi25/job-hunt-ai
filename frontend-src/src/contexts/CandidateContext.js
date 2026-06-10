import React, { createContext, useContext, useState } from 'react';

const CandidateContext = createContext();

export const useCandidate = () => {
  const context = useContext(CandidateContext);
  if (!context) {
    throw new Error('useCandidate must be used within a CandidateProvider');
  }
  return context;
};

export const CandidateProvider = ({ children }) => {
  const [candidateProfile, setCandidateProfile] = useState(null);
  const [resumeFile, setResumeFile] = useState(null);

  const updateCandidateProfile = (profile) => {
    setCandidateProfile(profile);
    // Also store in localStorage for persistence
    if (profile) {
      localStorage.setItem('candidateProfile', JSON.stringify(profile));
    } else {
      localStorage.removeItem('candidateProfile');
    }
  };

  const updateResumeFile = (file) => {
    setResumeFile(file);
  };

  const clearCandidateData = () => {
    setCandidateProfile(null);
    setResumeFile(null);
    localStorage.removeItem('candidateProfile');
  };

  // Load from localStorage on mount
  React.useEffect(() => {
    const stored = localStorage.getItem('candidateProfile');
    if (stored) {
      try {
        setCandidateProfile(JSON.parse(stored));
      } catch (error) {
        console.error('Error parsing stored candidate profile:', error);
        localStorage.removeItem('candidateProfile');
      }
    }
  }, []);

  const value = {
    candidateProfile,
    resumeFile,
    updateCandidateProfile,
    updateResumeFile,
    clearCandidateData
  };

  return (
    <CandidateContext.Provider value={value}>
      {children}
    </CandidateContext.Provider>
  );
};

