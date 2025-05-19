import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { jwtDecode } from 'jwt-decode';

const NaverCallback = ({ onLogin }) => {
  const [error, setError] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // URL에서 토큰과 사용자 정보 추출
    const queryParams = new URLSearchParams(location.search);
    const token = queryParams.get('token');
    const userDataString = queryParams.get('user');

    if (token) {
      try {
        // 토큰 디코딩 및 저장
        const decodedToken = jwtDecode(token);
        
        // 사용자 정보 파싱
        let userData = {};
        if (userDataString) {
          userData = JSON.parse(userDataString);
        }
        
        // 로컬 스토리지에 저장
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(userData));
        
        // 로그인 성공 콜백 호출
        if (onLogin) {
          onLogin(userData);
        }
        
        // 홈으로 리디렉션
        navigate('/');
      } catch (err) {
        console.error('토큰 처리 중 오류 발생:', err);
        setError('인증 처리 중 오류가 발생했습니다.');
      }
    } else if (queryParams.get('error')) {
      setError(`로그인 오류: ${queryParams.get('error_description') || queryParams.get('error')}`);
    } else {
      setError('인증 정보를 찾을 수 없습니다.');
    }
  }, [location, navigate, onLogin]);

  if (error) {
    return (
      <div className="error-container">
        <h2>로그인 오류</h2>
        <p>{error}</p>
        <button onClick={() => navigate('/')}>홈으로 돌아가기</button>
      </div>
    );
  }

  return (
    <div className="loading-container">
      <p>로그인 처리 중...</p>
    </div>
  );
};

export default NaverCallback; 