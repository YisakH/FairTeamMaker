import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';

// 인증 컨텍스트 생성
const AuthContext = createContext(null);

// 인증 컨텍스트 제공자 컴포넌트
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // 초기 로딩 시 로컬 스토리지에서 사용자 정보 가져오기
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const storedToken = localStorage.getItem('token');
        if (storedToken) {
          const storedUser = JSON.parse(localStorage.getItem('user') || '{}');
          setUser(storedUser);
          
          // 인증 토큰을 사용하여 API 요청 시 헤더 설정
          axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
        }
      } catch (error) {
        console.error('인증 확인 중 오류 발생:', error);
        logout();
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  // 로그인 함수
  const login = (userData) => {
    setUser(userData);
    setLoading(false);
  };

  // 로그아웃 함수
  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  // 인증 상태 확인 함수
  const isAuthenticated = () => {
    return !!user;
  };

  // 컨텍스트 값
  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// 인증 컨텍스트 사용을 위한 훅
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth는 AuthProvider 내부에서만 사용할 수 있습니다.');
  }
  return context;
};

export default AuthContext; 