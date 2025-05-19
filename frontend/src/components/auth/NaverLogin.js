import React, { useState, useEffect } from 'react';
import axios from 'axios';

// 네이버 로그인 버튼 스타일
const naverButtonStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  backgroundColor: '#03C75A',
  color: 'white',
  fontWeight: 'bold',
  padding: '10px 20px',
  borderRadius: '4px',
  border: 'none',
  cursor: 'pointer',
  width: '200px',
  textDecoration: 'none',
  fontSize: '14px',
  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)'
};

const NaverLogin = ({ onLoginSuccess }) => {
  const [loginUrl, setLoginUrl] = useState('');

  useEffect(() => {
    // 네이버 로그인 URL 가져오기
    const fetchNaverLoginUrl = async () => {
      try {
        const response = await axios.get('http://localhost:8000/auth/naver/login');
        setLoginUrl(response.data.auth_url);
      } catch (error) {
        console.error('네이버 로그인 URL을 가져오는 중 오류 발생:', error);
      }
    };

    fetchNaverLoginUrl();
  }, []);

  return (
    <a href={loginUrl} style={naverButtonStyle}>
      <span style={{ marginRight: '10px' }}>N</span> 네이버로 로그인
    </a>
  );
};

export default NaverLogin; 