from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
import secrets
import json
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# OAuth 설정
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_REDIRECT_URI = os.getenv("NAVER_REDIRECT_URI")

# JWT 설정
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))

# 프론트엔드 URL
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# 모델 정의
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    id: Optional[str] = None

class UserInfo(BaseModel):
    id: str
    email: str
    name: str
    profile_image: Optional[str] = None

# 라우터 설정
router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth2 비밀번호 베어러 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT 토큰 생성 함수
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

# 토큰 검증 함수
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, name=payload.get("name"), id=payload.get("id"))
    except JWTError:
        raise credentials_exception
    return token_data

# 네이버 로그인 URL 생성 엔드포인트
@router.get("/naver/login")
async def naver_login():
    """네이버 로그인 페이지로 리디렉션합니다."""
    state = secrets.token_hex(16)  # CSRF 방지를 위한 상태 토큰
    
    # 네이버 인증 URL 생성
    auth_url = f"https://nid.naver.com/oauth2.0/authorize?response_type=code&client_id={NAVER_CLIENT_ID}&redirect_uri={NAVER_REDIRECT_URI}&state={state}"
    
    return {"auth_url": auth_url, "state": state}

# 네이버 콜백 처리 엔드포인트
@router.get("/naver/callback")
async def naver_callback(code: str, state: str):
    """네이버 로그인 콜백을 처리합니다."""
    try:
        # 인증 코드를 이용하여 액세스 토큰 얻기
        token_url = "https://nid.naver.com/oauth2.0/token"
        token_data = {
            "grant_type": "authorization_code",
            "client_id": NAVER_CLIENT_ID,
            "client_secret": NAVER_CLIENT_SECRET,
            "code": code,
            "state": state
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)
            token_info = token_response.json()
            
            if "error" in token_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"네이버 인증 오류: {token_info['error']}"
                )
            
            # 네이버 API를 통해 사용자 정보 가져오기
            access_token = token_info["access_token"]
            profile_url = "https://openapi.naver.com/v1/nid/me"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            profile_response = await client.get(profile_url, headers=headers)
            profile_data = profile_response.json()
            
            if profile_data["resultcode"] != "00":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="사용자 정보를 가져오는데 실패했습니다."
                )
            
            # 사용자 정보 추출
            user_data = profile_data["response"]
            user_info = UserInfo(
                id=user_data["id"],
                email=user_data.get("email", ""),
                name=user_data.get("name", ""),
                profile_image=user_data.get("profile_image", "")
            )
            
            # JWT 토큰 생성
            access_token_expires = timedelta(minutes=JWT_EXPIRATION_MINUTES)
            access_token = create_access_token(
                data={"sub": user_info.email, "email": user_info.email, "name": user_info.name, "id": user_info.id},
                expires_delta=access_token_expires
            )
            
            # 프론트엔드로 리디렉션 (토큰 포함)
            redirect_url = f"{FRONTEND_URL}?token={access_token}&user={json.dumps(user_info.dict())}"
            return RedirectResponse(url=redirect_url)
            
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그인 처리 중 오류가 발생했습니다: {str(e)}"
        )

# 현재 사용자 정보 조회 엔드포인트
@router.get("/me", response_model=TokenData)
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    """현재 로그인한 사용자의 정보를 반환합니다."""
    return current_user 