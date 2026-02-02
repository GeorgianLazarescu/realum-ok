import React, { createContext, useContext, useState } from 'react';
import Confetti from 'react-confetti';

const ConfettiContext = createContext(null);

export const useConfetti = () => useContext(ConfettiContext);

export const ConfettiProvider = ({ children }) => {
  const [showConfetti, setShowConfetti] = useState(false);
  
  const triggerConfetti = () => {
    setShowConfetti(true);
    // Play celebration sound
    try {
      const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2teleT4ZZ5q9z7J+TyQwdqjE0KtzPBklb5+7yqxxORAjbKG+0a51RA0faZ69yK1zQQ4dcJW4xKpxPg8bc5m6xahxPw8Zc5S3w6ZvPBAXdJa5wqVuOxIWdZS4waNtORMUdpO3waJsNxUTdpK2v6FrNhYSd5G1vqBqNRcRd4+0vZ9pNBgQeI6zvJ5oMxkPeI2yvJ1nMhoOeoyxu5xmMRsNeYqwuZtlMBwMeoqwuZpkLx0Leomvt5ljLR4KeYiutphhLB8Jd4atsZZfKiEId4atsJVeKSIHdoSrr5RdKCMGdYOqrpNcJyQFdYKprZJbJiUFdIGprJFaJSYEdICoq5BZJCcDc3+nqo9YIygCc36mqY5XIikBcn2lqI1WISoBcnylp4xVICsBcXukpotUHywAcHqjpYpTHi0Ab3mipIlSHS4AbnihoohRHC8AbnehoogQGy8AbnehoodRGi8AbnehoodQGS8AbnahoodPFy8AbnahoodOFS8AbnWhoYZOFC8AbnWgoYVNEy8AbnWgoIRNEi8AbnWgoIRMES4AbnSfoINMEC4Abg==');
      audio.volume = 0.3;
      audio.play().catch(() => {});
    } catch (e) {}
    setTimeout(() => setShowConfetti(false), 5000);
  };
  
  return (
    <ConfettiContext.Provider value={{ triggerConfetti }}>
      {showConfetti && <Confetti recycle={false} numberOfPieces={200} />}
      {children}
    </ConfettiContext.Provider>
  );
};
