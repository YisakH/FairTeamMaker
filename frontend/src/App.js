import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { PlusIcon, TrashIcon, UserGroupIcon, CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';

// API 기본 URL을 환경변수에서 가져오고, 기본값은 백엔드 기본 포트로 설정
// (주의) 여기서는 '/api'와 같은 경로 접두사를 붙이지 않습니다.
const API_BASE_URL = '/api';

function App() {
  const [participants, setParticipants] = useState([]);
  const [attendingParticipants, setAttendingParticipants] = useState([]);
  const [newParticipant, setNewParticipant] = useState('');
  const [groups, setGroups] = useState([]);
  const [cooccurrenceInfo, setCooccurrenceInfo] = useState({});
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('attendance'); // 'manage', 'attendance', 'options', 'results', 'history', 'scores'
  const [generationMethod, setGenerationMethod] = useState('simulated_annealing');
  const [lambdaValue, setLambdaValue] = useState(0.7);
  const [showOptions, setShowOptions] = useState(false);
  const [methodUsed, setMethodUsed] = useState('');
  const [accumulateSameDay, setAccumulateSameDay] = useState(false);
  const [showConfirmPopup, setShowConfirmPopup] = useState(false);
  const [hasExistingDataToday, setHasExistingDataToday] = useState(false);
  const [teamHistory, setTeamHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [deleteConfirmDate, setDeleteConfirmDate] = useState(null);
  const [notification, setNotification] = useState({ show: false, message: '', type: '' });
  const [popover, setPopover] = useState({ show: false, x: 0, y: 0, anchorKey: '', title: '', lines: [], isMobile: false });
  const [selectedPersonMobile, setSelectedPersonMobile] = useState('');
  const [asOfDate, setAsOfDate] = useState(null); // 히스토리 상세 조회 시 기준 날짜
  const [deleteParticipantName, setDeleteParticipantName] = useState(null);
  const [latestTodayTimeText, setLatestTodayTimeText] = useState('');

  // 시뮬레이티드 어닐링 파라미터
  const [saParams, setSaParams] = useState({
    initial_temp: 100.0,
    cooling_rate: 0.995,
    temp_min: 0.1,
    max_iter: 5000
  });

  useEffect(() => {
    console.log('API_BASE_URL on component mount:', API_BASE_URL);
    fetchParticipants();
    fetchAttendingParticipants();
    fetchCooccurrenceInfo();
    
    // URL 해시를 확인하여 최근 결과 불러오기
    const hash = window.location.hash.substring(1); // # 제거
    if (hash === 'results') {
      // 최근 팀 히스토리 불러와서 results 뷰로 이동
      loadLatestTeamResult();
    }
    
    // Kakao SDK 초기화 - 스크립트 로딩을 기다림
    const initKakaoSDK = () => {
      if (window.Kakao) {
        if (!window.Kakao.isInitialized()) {
          try {
            window.Kakao.init('c42369797d199b2a47843b461ab2a38b');
            console.log('✅ Kakao SDK initialized:', window.Kakao.isInitialized());
          } catch (error) {
            console.error('❌ Kakao SDK 초기화 실패:', error);
          }
        } else {
          console.log('✅ Kakao SDK already initialized');
        }
      } else {
        console.log('⏳ Kakao SDK not loaded yet, waiting...');
        // SDK가 아직 로드되지 않았으면 0.5초 후 재시도
        setTimeout(initKakaoSDK, 500);
      }
    };
    
    // 초기화 시도
    initKakaoSDK();
  }, []);

  // 모바일 리스트 기준 인물 보정: 비어있을 경우 첫 참석자를 자동 선택
  useEffect(() => {
    if (!selectedPersonMobile && attendingParticipants && attendingParticipants.length > 0) {
      setSelectedPersonMobile(attendingParticipants[0]);
    }
  }, [attendingParticipants, selectedPersonMobile]);

  // 람다값이 변경되면 cooccurrence 정보 다시 불러오기
  useEffect(() => {
    fetchCooccurrenceInfo(asOfDate);
  }, [lambdaValue, asOfDate]);

  const fetchParticipants = async () => {
    try {
      const requestUrl = `${API_BASE_URL}/participants`;
      console.log(`[API 요청] 참가자 목록: ${requestUrl}`);
      const response = await axios.get(requestUrl);
      setParticipants(response.data);
    } catch (error) {
      console.error(`니가 별 짓을 다 했지만 나는 ${API_BASE_URL + '/participants'} 여기로 보냈지롱`);
      console.error('참가자 목록을 불러오는데 실패했습니다:', error);
    }
  };

  const fetchAttendingParticipants = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/attending`);
      setAttendingParticipants(response.data);
      console.log(`no bug: ${API_BASE_URL}/attending 여기로 보냈지롱`);
      // 모바일 기준 인물 기본값 세팅
      if (response.data && response.data.length > 0) {
        setSelectedPersonMobile(prev => response.data.includes(prev) ? prev : response.data[0]);
      } else {
        setSelectedPersonMobile('');
      }
    } catch (error) {
      console.error(`니가 별 짓을 다 했지만 나는 ${API_BASE_URL + '/participants'} 여기로 보냈지롱`);
      console.error('참석자 목록을 불러오는데 실패했습니다ㅋㅋㅋㅋㅋㅋ:', error);
    }
  };

  const fetchCooccurrenceInfo = async (asOf = null) => {
    try {
      const params = { lam: lambdaValue };
      if (asOf) params.as_of = asOf; // ISO 그대로 전달 (시각 포함)
      const response = await axios.get(`${API_BASE_URL}/cooccurrence`, { params });
      setCooccurrenceInfo(response.data);
    } catch (error) {
      console.error('공동 참여 정보를 불러오는데 실패했습니다:', error);
    }
  };

  // 페어 정보 헬퍼들
  const getPairInfo = (a, b) => {
    if (!a || !b || a === b) return null;
    return cooccurrenceInfo?.[a]?.[b] || null;
  };

  // 등급(A-D) 계산을 위한 헬퍼들
  const getQuartileThresholds = (names) => {
    const values = [];
    for (let i = 0; i < names.length; i++) {
      for (let j = 0; j < names.length; j++) {
        if (i === j) continue;
        const a = names[i], b = names[j];
        const info = getPairInfo(a, b);
        if (info && typeof info.time_decay_weight === 'number') {
          values.push(info.time_decay_weight);
        }
      }
    }
    if (values.length === 0) return [0, 0, 0];
    values.sort((x, y) => x - y);
    const q1 = values[Math.floor(values.length * 0.25)];
    const q2 = values[Math.floor(values.length * 0.50)];
    const q3 = values[Math.floor(values.length * 0.75)];
    return [q1, q2, q3];
  };

  const gradeFromValue = (v, [q1, q2, q3]) => {
    // 낮을수록 선호 (첫만남 보너스로 음수 가능)
    if (v <= q1) return 'A';
    if (v <= q2) return 'B';
    if (v <= q3) return 'C';
    return 'D';
  };

  const gradeColor = (g) => {
    switch (g) {
      case 'A': return 'bg-green-100 text-green-800';
      case 'B': return 'bg-blue-100 text-blue-800';
      case 'C': return 'bg-yellow-100 text-yellow-800';
      case 'D': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  // 팝오버 열기/닫기
  const openPopover = (event, title, lines, anchorKey) => {
    const isMobile = window.innerWidth < 768; // md 미만
    if (isMobile) {
      setPopover({ show: true, x: 0, y: 0, title, lines, anchorKey, isMobile: true });
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + window.scrollY + rect.height + 8; // 셀 아래 8px
    setPopover({ show: true, x, y, title, lines, anchorKey, isMobile: false });
  };
  const closePopover = () => setPopover(prev => ({ ...prev, show: false }));

  const addParticipant = async (e) => {
    e.preventDefault();
    if (!newParticipant.trim()) return;

    try {
      await axios.post(`${API_BASE_URL}/participants`, { name: newParticipant });
      setNewParticipant('');
      fetchParticipants();
      fetchCooccurrenceInfo();
    } catch (error) {
      console.error('참가자 추가에 실패했습니다:', error);
    }
  };

  const removeParticipant = async (name) => {
    try {
      await axios.delete(`${API_BASE_URL}/participants/${name}`);
      fetchParticipants();
      fetchAttendingParticipants();
      fetchCooccurrenceInfo();
    } catch (error) {
      console.error('참가자 제거에 실패했습니다:', error);
    }
  };

  const updateAttendance = async (name, attending) => {
    try {
      await axios.post(`${API_BASE_URL}/attendance`, { name, attending });
      fetchAttendingParticipants();
    } catch (error) {
      console.error('참석 여부 업데이트에 실패했습니다:', error);
    }
  };

  const resetAttendance = async () => {
    try {
      await axios.post(`${API_BASE_URL}/reset-attendance`);
      fetchAttendingParticipants();
    } catch (error) {
      console.error('참석자 초기화에 실패했습니다:', error);
    }
  };

  const handleSaParamChange = (param, value) => {
    setSaParams(prev => ({
      ...prev,
      [param]: value
    }));
  };

  const checkTodayData = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/has-today-data`);
      const exists = response.data.has_today_data;
      const latestTime = response.data.latest_time;
      if (exists) {
        let friendly = '엇, 오늘 이미 조를 짜셨네요! 추가로 한 번 더 만드시겠어요?';
        if (latestTime) {
          try {
            const dt = new Date(latestTime);
            const t = dt.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
            friendly = `엇, 오늘 ${t}에 이미 조를 짜셨네요! 추가로 한 번 더 만드시겠어요?`;
          } catch (e) {
            // ignore parsing error, keep default
          }
        }
        setLatestTodayTimeText(friendly);
        setHasExistingDataToday(true);
        setShowConfirmPopup(true);
      } else {
        // 오늘 데이터가 없으면 바로 조 생성 진행
        generateTeamsExecute(false);
      }
    } catch (error) {
      console.error('오늘 데이터 확인에 실패했습니다:', error);
      // 에러 발생 시 바로 조 생성 진행
      generateTeamsExecute(false);
    }
  };

  const generateTeams = async () => {
    // 먼저 오늘 데이터 존재 여부 확인
    checkTodayData();
  };

  const generateTeamsExecute = async (preserveExisting) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/generate`, {
        participants: attendingParticipants,
        window_days: 60,
        lam: lambdaValue,
        method: generationMethod,
        sa_params: generationMethod === 'simulated_annealing' ? saParams : null,
        accumulate_same_day: preserveExisting // 팝업에서 선택한 값 적용
      });
      setGroups(response.data.groups);
      setCooccurrenceInfo(response.data.cooccurrence_info);
      setMethodUsed(response.data.method_used);
      setAsOfDate(null); // 현재 시점 생성이므로 as-of 해제
      setView('results');
    } catch (error) {
      console.error('조 생성에 실패했습니다:', error);
    }
    setLoading(false);
    setShowConfirmPopup(false);
  };

  const isAttending = (name) => {
    return attendingParticipants.includes(name);
  };

  const toggleAllAttendance = () => {
    if (attendingParticipants.length === participants.length) {
      // 모두 참석 중이면 전체 참석 취소
      resetAttendance();
    } else {
      // 아니면 전체 참석 처리
      Promise.all(participants.map(p => updateAttendance(p, true)))
        .then(() => fetchAttendingParticipants())
        .catch(error => console.error('전체 참석 설정에 실패했습니다:', error));
    }
  };

  // 팀 생성 기록 불러오기
  const fetchTeamHistory = async () => {
    setLoadingHistory(true);
    try {
      const requestUrl = `${API_BASE_URL}/team-history`;
      console.log(`[API 요청] 팀 생성 기록: ${requestUrl}`);
      const response = await axios.get(requestUrl);
      setTeamHistory(response.data.history);
    } catch (error) {
      console.error('팀 생성 기록을 불러오는데 실패했습니다:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  // 팀 생성 기록 삭제
  const deleteTeamHistory = async (date) => {
    try {
      await axios.delete(`${API_BASE_URL}/team-history/${date}`);
      // 기록 다시 불러오기
      fetchTeamHistory();
      setDeleteConfirmDate(null);
    } catch (error) {
      console.error('팀 생성 기록 삭제에 실패했습니다:', error);
    }
  };

  // 모든 팀 생성 기록 삭제
  const deleteAllTeamHistory = async () => {
    try {
      await axios.delete(`${API_BASE_URL}/team-history`);
      // 기록 다시 불러오기
      fetchTeamHistory();
    } catch (error) {
      console.error('팀 생성 기록 삭제에 실패했습니다:', error);
    }
  };

  // 오늘 날짜의 팀 데이터만 삭제
  const deleteTodayData = async () => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/today-data`);
      console.log('최근 조 삭제 결과:', response.data);
      // 기록 다시 불러오기
      fetchTeamHistory();
      // 알림 메시지 설정
      setNotification({
        show: true,
        message: `가장 최근에 생성된 조 데이터가 삭제되었습니다. (${response.data.stats.deleted_cooccurrence_items}개 항목 삭제)`,
        type: 'success'
      });
      // 5초 후 알림 숨기기
      setTimeout(() => setNotification({...notification, show: false}), 5000);
    } catch (error) {
      console.error('최근 조 삭제에 실패했습니다:', error);
      setNotification({
        show: true,
        message: '최근 조 삭제에 실패했습니다.',
        type: 'error'
      });
      setTimeout(() => setNotification({...notification, show: false}), 5000);
    }
  };

  // 날짜 및 시간 포맷팅 함수
  const formatDateTime = (isoString) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return isoString;
    }
  };

  // 팀 결과 뷰로 전환하고 과거 기록에서 팀 데이터 불러오기
  const loadHistoryTeam = (historyItem) => {
    setGroups(historyItem.groups);
    setMethodUsed(historyItem.method_used);
    setLambdaValue(historyItem.lambda_value);
    setAsOfDate(historyItem.date);
    setCooccurrenceInfo({});
    // 과거 시점 기준 공동참여/가중치 정보를 즉시 재요청
    fetchCooccurrenceInfo(historyItem.date);
    setView('results');
  };

  // 가장 최근 팀 결과 불러오기 (URL 해시 처리용)
  const loadLatestTeamResult = async () => {
    try {
      const requestUrl = `${API_BASE_URL}/team-history`;
      console.log(`[API 요청] 최근 팀 결과: ${requestUrl}`);
      const response = await axios.get(requestUrl);
      const history = response.data.history;
      
      if (history && history.length > 0) {
        // 가장 최근 기록을 불러옴 (배열의 마지막 요소가 가장 최근)
        const latestTeam = history[history.length - 1];
        loadHistoryTeam(latestTeam);
      } else {
        // 기록이 없으면 기본 뷰로
        setView('attendance');
      }
    } catch (error) {
      console.error('최근 팀 결과를 불러오는데 실패했습니다:', error);
      setView('attendance');
    }
  };

  // 카카오톡으로 공유하기
  const shareToKakao = () => {
    console.log('shareToKakao called');
    console.log('window.Kakao:', window.Kakao);
    console.log('isInitialized:', window.Kakao ? window.Kakao.isInitialized() : 'N/A');
    
    if (!window.Kakao) {
      alert('카카오톡 SDK가 로드되지 않았습니다. 페이지를 새로고침해보세요.');
      copyTeamText();
      return;
    }
    
    if (!window.Kakao.isInitialized()) {
      alert('카카오톡 SDK가 초기화되지 않았습니다. 페이지를 새로고침해보세요.');
      copyTeamText();
      return;
    }

    try {
      // 팀 정보를 텍스트로 포맷팅
      const teamText = formatTeamText();
      
      // 현재 URL에 results 뷰로 이동하는 해시 추가
      const currentUrl = window.location.origin + window.location.pathname;
      const shareUrl = `${currentUrl}#results`;
      
      window.Kakao.Share.sendDefault({
        objectType: 'text',
        text: teamText,
        link: {
          mobileWebUrl: shareUrl,
          webUrl: shareUrl,
        },
      });
      
      console.log('카카오톡 공유 성공');
    } catch (error) {
      console.error('카카오톡 공유 실패:', error);
      alert('카카오톡 공유에 실패했습니다. 텍스트를 복사합니다.');
      copyTeamText();
    }
  };

  // 팀 정보를 텍스트로 포맷팅
  const formatTeamText = () => {
    const dateStr = asOfDate 
      ? new Date(asOfDate).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
      : new Date().toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' });
    
    let text = `📋 ${dateStr} 팀 구성 결과\n\n`;
    
    groups.forEach((group, index) => {
      text += `🔹 조 ${index + 1} (${group.length}명)\n`;
      text += `${group.join(', ')}\n\n`;
    });
    
    text += `✨ 총 ${groups.length}개 조, ${groups.flat().length}명 참여`;
    
    return text;
  };

  // 팀 정보를 클립보드에 복사
  const copyTeamText = () => {
    const teamText = formatTeamText();
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(teamText)
        .then(() => {
          setNotification({
            show: true,
            message: '팀 구성이 클립보드에 복사되었습니다! 카카오톡에 붙여넣기 하세요.',
            type: 'success'
          });
          setTimeout(() => setNotification({...notification, show: false}), 3000);
        })
        .catch(err => {
          console.error('복사 실패:', err);
          alert('클립보드 복사에 실패했습니다.');
        });
    } else {
      // 구형 브라우저 대응
      const textArea = document.createElement('textarea');
      textArea.value = teamText;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      try {
        document.execCommand('copy');
        setNotification({
          show: true,
          message: '팀 구성이 클립보드에 복사되었습니다! 카카오톡에 붙여넣기 하세요.',
          type: 'success'
        });
        setTimeout(() => setNotification({...notification, show: false}), 3000);
      } catch (err) {
        console.error('복사 실패:', err);
        alert('클립보드 복사에 실패했습니다.');
      }
      
      document.body.removeChild(textArea);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 overflow-x-hidden">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">HieL Team Maker 🎲</h1>

        {/* 알림 메시지 */}
        {notification.show && (
          <div className={`mb-4 p-3 rounded-md ${notification.type === 'error' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
            {notification.message}
            <button 
              onClick={() => setNotification({...notification, show: false})}
              className="ml-2 text-sm font-medium hover:text-opacity-75"
            >
              ✕
            </button>
          </div>
        )}

        {/* 탭 메뉴 */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex flex-wrap gap-2 sm:gap-8">
            <button
              onClick={() => setView('attendance')}
              className={`${view === 'attendance' 
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } py-2 px-2 border-b-2 font-medium text-xs sm:text-sm break-words basis-[48%] sm:basis-auto`}
            >
              참석 여부 관리
            </button>
            
            <button
              onClick={() => {
                setView('history');
                fetchTeamHistory();
              }}
              className={`${view === 'history' 
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } py-2 px-2 border-b-2 font-medium text-xs sm:text-sm break-words basis-[48%] sm:basis-auto`}
            >
              조 기록 보기
            </button>
            {groups.length > 0 && (
              <button
                onClick={() => setView('results')}
                className={`${view === 'results' 
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } py-2 px-2 border-b-2 font-medium text-xs sm:text-sm break-words basis-[48%] sm:basis-auto`}
              >
                결과 보기
              </button>
            )}
            <button
              onClick={() => setView('options')}
              className={`${view === 'options' 
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } py-2 px-2 border-b-2 font-medium text-xs sm:text-sm break-words basis-[48%] sm:basis-auto`}
            >
              조 생성 옵션
            </button>
            <button
              onClick={() => setView('scores')}
              className={`${view === 'scores' 
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } py-2 px-2 border-b-2 font-medium text-xs sm:text-sm break-words basis-[48%] sm:basis-auto`}
            >
              조 매칭 정보
            </button>
          </nav>
        </div>

        

        {view === 'attendance' && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-lg font-semibold">이번 주 출석 인원</h2>
              <div className="flex space-x-2">
                <button
                  onClick={toggleAllAttendance}
                  className="inline-flex items-center px-2 py-1 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  {attendingParticipants.length === participants.length ? '전체 해제' : '전체 선택'}
                </button>
                <button
                  onClick={resetAttendance}
                  className="inline-flex items-center px-2 py-1 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  초기화
                </button>
              </div>
            </div>

            {/* 참석 여부 관리 내 참가자 추가 */}
            <form onSubmit={addParticipant} className="flex gap-2 mb-3">
              <input
                type="text"
                value={newParticipant}
                onChange={(e) => setNewParticipant(e.target.value)}
                placeholder="명단에 없는 새로운 팀원 추가"
                className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 py-1.5 px-2 text-sm"
              />
              <button
                type="submit"
                className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-1 focus:ring-offset-1 focus:ring-indigo-500"
              >
                <PlusIcon className="h-4 w-4 mr-1" />
                추가
              </button>
            </form>

            {/* 모바일 최적화: 그리드를 2열 또는 3열로 설정하고 참가자 카드를 콤팩트하게 변경 */}
            <div className="mt-2 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-2">
              {participants.map((name) => (
                <div
                  key={name}
                  className={`border rounded-md px-2 py-1.5 ${isAttending(name) ? 'border-green-500 bg-green-50' : 'border-gray-300'}`}
                >
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        className="hidden"
                        checked={isAttending(name)}
                        onChange={(e) => updateAttendance(name, e.target.checked)}
                      />
                      <span 
                        className={`inline-flex items-center justify-center w-5 h-5 rounded-full flex-shrink-0 ${
                          isAttending(name) 
                            ? 'bg-green-500 text-white' 
                            : 'bg-gray-200 text-gray-400'
                        }`}
                      >
                        {isAttending(name) ? (
                          <CheckIcon className="h-3 w-3" />
                        ) : (
                          <XMarkIcon className="h-3 w-3" />
                        )}
                      </span>
                      <span className={`text-xs font-medium truncate ${isAttending(name) ? 'text-green-900' : 'text-gray-700'}`}>
                        {name}
                      </span>
                    </label>
                    <button
                      type="button"
                      onClick={() => setDeleteParticipantName(name)}
                      className="text-gray-400 hover:text-red-500 p-1"
                      title="삭제"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-3 text-right text-xs text-gray-500">
              <p>총 참가자: {participants.length}명 / 참석자: {attendingParticipants.length}명</p>
            </div>
          </div>
        )}

        {view === 'options' && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <h2 className="text-lg font-semibold mb-3">조 생성 옵션</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  조 생성 방법
                </label>
                <div className="flex flex-wrap items-center gap-3">
                  <label className="inline-flex items-center">
                    <input
                      type="radio"
                      value="weighted_random"
                      checked={generationMethod === 'weighted_random'}
                      onChange={() => setGenerationMethod('weighted_random')}
                      className="h-3 w-3 text-indigo-600 border-gray-300 focus:ring-indigo-500"
                    />
                    <span className="ml-1.5 text-xs text-gray-700">
                      가중치 랜덤 (간단)
                    </span>
                  </label>
                  <label className="inline-flex items-center">
                    <input
                      type="radio"
                      value="simulated_annealing"
                      checked={generationMethod === 'simulated_annealing'}
                      onChange={() => setGenerationMethod('simulated_annealing')}
                      className="h-3 w-3 text-indigo-600 border-gray-300 focus:ring-indigo-500"
                    />
                    <span className="ml-1.5 text-xs text-gray-700">
                      시뮬레이티드 어닐링 (최적화)
                    </span>
                  </label>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  * 참석자가 8명 미만일 경우 자동으로 가중치 랜덤 방식이 사용됩니다.
                </p>
                
                <div className="mt-2 p-2 bg-blue-50 rounded-md text-xs text-blue-800">
                  <p className="font-medium mb-1">알고리즘 설명:</p>
                  <ul className="list-disc pl-4 space-y-0.5">
                    <li><strong>가중치 랜덤</strong>: 이전에 같은 조였던 사람들을 피해서 랜덤하게 팀을 구성합니다.</li>
                    <li><strong>시뮬레이티드 어닐링 (추천)</strong>: 최적화 알고리즘을 사용하여 이전 조 구성을 고려한 최적의 팀을 구성합니다.</li>
                  </ul>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  람다 값 (λ): {lambdaValue}
                </label>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">0.0</span>
                  <input
                    type="range"
                    min="0.0"
                    max="3.0"
                    step="0.1"
                    value={lambdaValue}
                    onChange={(e) => setLambdaValue(parseFloat(e.target.value))}
                    className="flex-1 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <span className="text-xs text-gray-500">3.0</span>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  값이 클수록 이전 조 구성원과 겹치지 않도록 더 강하게 제한합니다.
                </p>
                <div className="mt-1 bg-yellow-50 p-2 rounded-md text-xs text-yellow-800">
                  <p>람다 값이 클수록 회피 점수가 높은 조합을 더 강하게 피합니다.</p>
                </div>
              </div>

              {generationMethod === 'simulated_annealing' && (
                <div>
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-medium text-gray-700">
                      시뮬레이티드 어닐링 세부 설정
                    </label>
                    <button
                      type="button"
                      onClick={() => setShowOptions(!showOptions)}
                      className="text-xs text-indigo-600 hover:text-indigo-500"
                    >
                      {showOptions ? '접기' : '펼치기'}
                    </button>
                  </div>

                  {showOptions && (
                    <div className="mt-2 space-y-3 p-3 bg-gray-50 rounded-md">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          초기 온도: {saParams.initial_temp}
                        </label>
                        <input
                          type="range"
                          min="50"
                          max="200"
                          step="10"
                          value={saParams.initial_temp}
                          onChange={(e) => handleSaParamChange('initial_temp', parseFloat(e.target.value))}
                          className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <p className="mt-0.5 text-xs text-gray-500">
                          초기 온도가 높을수록 처음에 더 무작위적인 탐색을 수행합니다.
                        </p>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          냉각률: {saParams.cooling_rate}
                        </label>
                        <input
                          type="range"
                          min="0.9"
                          max="0.999"
                          step="0.001"
                          value={saParams.cooling_rate}
                          onChange={(e) => handleSaParamChange('cooling_rate', parseFloat(e.target.value))}
                          className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <p className="mt-0.5 text-xs text-gray-500">
                          값이 1에 가까울수록 온도가 느리게 감소하여 더 많은 탐색을 합니다.
                        </p>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          최소 온도: {saParams.temp_min}
                        </label>
                        <input
                          type="range"
                          min="0.01"
                          max="1"
                          step="0.01"
                          value={saParams.temp_min}
                          onChange={(e) => handleSaParamChange('temp_min', parseFloat(e.target.value))}
                          className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <p className="mt-0.5 text-xs text-gray-500">
                          알고리즘이 종료되는 최소 온도 값입니다.
                        </p>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          최대 반복 횟수: {saParams.max_iter}
                        </label>
                        <input
                          type="range"
                          min="1000"
                          max="10000"
                          step="1000"
                          value={saParams.max_iter}
                          onChange={(e) => handleSaParamChange('max_iter', parseInt(e.target.value))}
                          className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                        />
                        <p className="mt-0.5 text-xs text-gray-500">
                          알고리즘이 실행할 최대 반복 횟수입니다.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* 조 생성 버튼 */}
        {view !== 'results' && (
          <div className="flex justify-center mb-8">
            <button
              onClick={generateTeams}
              disabled={loading || attendingParticipants.length < 4}
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400"
            >
              <UserGroupIcon className="h-6 w-6 mr-2" />
              {loading ? '조 생성 중...' : '참석자로 조 생성하기'}
            </button>
          </div>
        )}

        {/* 생성된 조 목록 */}
        {view === 'results' && groups.length > 0 && (
          <div className="space-y-4">
            {/* 조 목록 (상단으로 이동) */}
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex justify-between items-center mb-3">
                <h2 className="text-lg font-semibold">조 구성</h2>
                <div className="flex gap-2">
                  <button
                    onClick={shareToKakao}
                    className="inline-flex items-center px-3 py-1.5 border border-yellow-400 text-xs font-medium rounded-md text-gray-800 bg-yellow-300 hover:bg-yellow-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
                    title="카카오톡으로 공유하기"
                  >
                    <svg className="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 3c5.799 0 10.5 3.664 10.5 8.185 0 4.52-4.701 8.184-10.5 8.184a13.5 13.5 0 0 1-1.727-.11l-4.408 2.883c-.501.265-.678.236-.472-.413l.892-3.678c-2.88-1.46-4.785-3.99-4.785-6.866C1.5 6.665 6.201 3 12 3zm5.907 8.06l1.47-1.424a.472.472 0 0 0-.656-.681l-1.928 1.866V9.282a.472.472 0 0 0-.944 0v2.557a.471.471 0 0 0 0 .222V13.5a.472.472 0 0 0 .944 0v-1.363l.427-.413 1.428 2.033a.472.472 0 1 0 .773-.543l-1.514-2.155zm-2.958 1.924h-1.46V9.297a.472.472 0 0 0-.943 0v4.159c0 .26.21.472.471.472h1.932a.472.472 0 1 0 0-.944zm-5.857-1.092l.696-1.707.638 1.707H9.092zm2.523.488l.002-.016a.469.469 0 0 0-.127-.32l-1.046-2.8a.69.69 0 0 0-.627-.474.696.696 0 0 0-.653.447l-1.661 4.075a.472.472 0 0 0 .874.357l.33-.813h2.07l.299.8a.472.472 0 1 0 .884-.33l-.345-.926zM8.293 9.302a.472.472 0 0 0-.471-.472H4.577a.472.472 0 1 0 0 .944h1.16v3.736a.472.472 0 0 0 .944 0V9.774h1.14c.261 0 .472-.212.472-.472z"/>
                    </svg>
                    카톡 공유
                  </button>
                  <button
                    onClick={copyTeamText}
                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    title="텍스트 복사"
                  >
                    <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    복사
                  </button>
                </div>
              </div>
              
              <div className="mb-3 p-2 bg-gray-50 rounded-md text-xs">
                <div className="grid grid-cols-2 gap-1">
                  <div className="flex items-center">
                    <span className="inline-flex items-center justify-center w-4 h-4 rounded text-[10px] font-semibold bg-green-100 text-green-800 mr-1">A</span>
                    <span>최우선 (새로운 만남)</span>
                  </div>
                  <div className="flex items-center">
                    <span className="inline-flex items-center justify-center w-4 h-4 rounded text-[10px] font-semibold bg-blue-100 text-blue-800 mr-1">B</span>
                    <span>우선 (가끔 만남)</span>
                  </div>
                  <div className="flex items-center">
                    <span className="inline-flex items-center justify-center w-4 h-4 rounded text-[10px] font-semibold bg-yellow-100 text-yellow-800 mr-1">C</span>
                    <span>보통 (종종 만남)</span>
                  </div>
                  <div className="flex items-center">
                    <span className="inline-flex items-center justify-center w-4 h-4 rounded text-[10px] font-semibold bg-red-100 text-red-800 mr-1">D</span>
                    <span>후순위 (자주 만남)</span>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 gap-3">
                {groups.map((group, index) => (
                  <div
                    key={index}
                    className="bg-gray-50 rounded-lg overflow-hidden border border-gray-200"
                  >
                    <div className="bg-indigo-600 text-white px-3 py-2">
                      <h3 className="text-base font-medium">
                        조 {index + 1} ({group.length}명)
                      </h3>
                    </div>
                    <div className="p-3">
                      {/* 조 멤버 */}
                      <div className="flex flex-wrap gap-1 mb-2">
                        {group.map((member) => (
                          <span 
                            key={member}
                            className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800"
                          >
                            {member}
                          </span>
                        ))}
                      </div>
                      
                      {/* 상세 정보 토글 (등급 표시) */}
                      <div className="mt-1 border-t border-gray-200 pt-2">
                        <details className="text-xs text-gray-600">
                          <summary className="font-medium cursor-pointer hover:text-indigo-600 flex items-center">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                            </svg>
                            이 조는 어떻게 짜졌냐면요...
                          </summary>
                          <div className="mt-2 space-y-2">
                            {group.map((member) => (
                              <div key={member} className="bg-white rounded-md p-2 shadow-sm">
                                <div className="font-medium text-gray-900 mb-1 text-xs">{member} 조 매칭 정보</div>
                                <div className="text-xs text-gray-500 space-y-1">
                                  {group.map((other) => {
                                    if (other === member) return null;
                                    const info = getPairInfo(member, other);
                                    if (!info) return null;

                                    let lastMet = "";
                                    if (info.last_occurrence) {
                                      try {
                                        const lastDate = new Date(info.last_occurrence);
                                        lastMet = `, 마지막: ${lastDate.toLocaleDateString('ko-KR')}`;
                                      } catch (e) {}
                                    }
                                    // 등급 계산 (히스토리 상세면 당시 조 구성원 기준, 아니면 현재 참석자 기준)
                                    const baseNames = asOfDate ? Array.from(new Set(groups.flat())) : attendingParticipants;
                                    const thresholds = getQuartileThresholds(baseNames);
                                    const grade = gradeFromValue(info.time_decay_weight, thresholds);

                                    return (
                                      <div key={other} className="py-1 border-b border-gray-100">
                                        <div className="flex items-center justify-between">
                                          <span className="text-gray-700">{other}</span>
                                          <div className="flex items-center gap-2">
                                            <span className="text-gray-500">{info.count}회</span>
                                            <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${gradeColor(grade)}`}>{grade}</span>
                                          </div>
                                        </div>
                                        <div className="text-[10px] text-gray-400 mt-0.5">{lastMet}</div>
                                      </div>
                                    );
                                  }).filter(Boolean)}
                                  
                                  {group.every(other => other === member || !cooccurrenceInfo[member]?.[other]) && (
                                    <div className="text-gray-400 italic py-1 text-xs">같은 조 이력 없음</div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* 결과 요약 정보 (하단으로 이동) */}
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex justify-between items-center mb-3">
                <h2 className="text-lg font-semibold">조 생성 결과</h2>
                <button
                  onClick={() => setView('attendance')}
                  className="inline-flex items-center px-2 py-1 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  다시 생성하기
                </button>
              </div>
              
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-blue-50 rounded-lg p-2 border border-blue-100">
                  <div className="text-blue-700 font-medium">생성 방법</div>
                  <div className="font-semibold mt-1">
                    {methodUsed === 'simulated_annealing' ? '최적화' : '랜덤'}
                  </div>
                </div>
                
                <div className="bg-green-50 rounded-lg p-2 border border-green-100">
                  <div className="text-green-700 font-medium">참석자</div>
                  <div className="font-semibold mt-1">{attendingParticipants.length}명</div>
                </div>
                
                <div className="bg-purple-50 rounded-lg p-2 border border-purple-100">
                  <div className="text-purple-700 font-medium">조 수</div>
                  <div className="font-semibold mt-1">{groups.length}개</div>
                </div>
              </div>
              
              <div className="mt-2 text-xs text-gray-500">
                람다 값(λ): {lambdaValue} · {new Date().toLocaleDateString('ko-KR')} 생성
              </div>
            </div>
          </div>
        )}

        {/* 매칭 등급 매트릭스 (A-D) */}
        {view === 'scores' && (
          <div className="bg-white rounded-lg shadow p-4 mb-6 overflow-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold">조 매칭 정보</h3>
              <div className="text-xs text-gray-500">람다(λ): {lambdaValue}</div>
            </div>

            <div className="mb-4 p-3 bg-blue-50 rounded-md border border-blue-200">
              <div className="text-sm font-medium text-blue-900 mb-2">💡 조 매칭 등급 안내</div>
              <div className="text-xs text-blue-800 space-y-1">
                <p>• <strong>A등급 (최우선)</strong>: 처음 만나거나 오래전에 만난 조합 - 새로운 만남 우선</p>
                <p>• <strong>B등급 (우선)</strong>: 가끔 만난 조합 - 적당한 빈도</p>
                <p>• <strong>C등급 (보통)</strong>: 종종 만난 조합 - 보통 빈도</p>
                <p>• <strong>D등급 (후순위)</strong>: 자주 만난 조합 - 가능하면 피함</p>
                <p className="pt-1 border-t border-blue-300 text-blue-700">
                  <strong>조 생성 시 A등급부터 우선적으로 고려하여 공정한 팀을 만듭니다.</strong>
                </p>
              </div>
            </div>

            <div className="mb-2 text-xs text-gray-600">
              <p>현재 참석자들 간의 과거 조 구성 이력을 바탕으로 매칭 등급을 표시합니다.</p>
            </div>

            {attendingParticipants.length < 2 ? (
              <div className="text-sm text-gray-500">참석자를 2명 이상 선택하세요.</div>
            ) : (
              <>
                {/* 모바일: 단일 기준 인물 선택 후 등급 리스트 */}
                <div className="md:hidden">
                  <div className="flex items-center gap-2 mb-2">
                    <label className="text-xs text-gray-600">기준 인물</label>
                    <select
                      className="text-xs border border-gray-300 rounded px-2 py-1 bg-white"
                      value={selectedPersonMobile}
                      onChange={(e) => setSelectedPersonMobile(e.target.value)}
                    >
                      {attendingParticipants.length === 0 && (
                        <option value="" disabled>선택 없음</option>
                      )}
                      {attendingParticipants.map(name => (
                        <option key={`opt-${name}`} value={name}>{name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="divide-y divide-gray-200 border border-gray-200 rounded-md overflow-hidden">
                    {(() => {
                      const base = selectedPersonMobile;
                      const baseNames = asOfDate ? Array.from(new Set(groups.flat())) : attendingParticipants;
                      const thresholds = getQuartileThresholds(baseNames);
                      return attendingParticipants
                        .filter(name => name !== base)
                        .map(name => {
                          const info = getPairInfo(base, name);
                          if (!info) return (
                            <div key={`m-${name}`} className="px-3 py-2 text-xs text-gray-400">{name} · N/A</div>
                          );
                          const grade = gradeFromValue(info.time_decay_weight, thresholds);
                          const cls = gradeColor(grade);
                          const anchorKey = `${base}-${name}`;
                          const lines = [
                            `총 ${info.count}회 만남`,
                            ...(Array.isArray(info.occurrence_dates) && info.occurrence_dates.length > 0
                              ? info.occurrence_dates.map(d => {
                                  try { return new Date(d).toLocaleDateString('ko-KR'); } catch (e) { return d; }
                                })
                              : ['기록 없음'])
                          ];
                          return (
                            <button
                              key={`m-${name}`}
                              type="button"
                              onClick={(e) => openPopover(e, `${base} · ${name}`, lines, anchorKey)}
                              className="w-full flex items-center justify-between px-3 py-2 bg-white hover:bg-gray-50"
                            >
                              <span className="text-xs text-gray-700">{name}</span>
                              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold ${cls}`}>{grade}</span>
                            </button>
                          );
                        });
                    })()}
                  </div>
                </div>

                {/* 데스크톱: 전체 매트릭스 */}
                <div className="hidden md:block w-full overflow-auto">
                  <table className="min-w-full border-separate" style={{ borderSpacing: 0 }}>
                    <thead>
                      <tr>
                        <th className="sticky left-0 z-10 bg-white border-b border-gray-200 text-left text-xs font-medium text-gray-500 px-2 py-1">이름</th>
                        {attendingParticipants.map(name => (
                          <th key={`col-${name}`} className="border-b border-gray-200 text-left text-xs font-medium text-gray-500 px-2 py-1 whitespace-nowrap">{name}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(() => {
                        const baseNames = asOfDate ? Array.from(new Set(groups.flat())) : attendingParticipants;
                        const thresholds = getQuartileThresholds(baseNames);
                        return attendingParticipants.map(rowName => (
                          <tr key={`row-${rowName}`}>
                            <th className="sticky left-0 z-10 bg-white border-b border-gray-100 text-xs font-medium text-gray-700 px-2 py-1 whitespace-nowrap">{rowName}</th>
                            {attendingParticipants.map(colName => {
                              if (rowName === colName) {
                                return (
                                  <td key={`${rowName}-${colName}`} className="border-b border-gray-100 px-2 py-1 text-center text-[10px] text-gray-400">—</td>
                                );
                              }
                              const info = getPairInfo(rowName, colName);
                              if (!info) {
                                return (
                                  <td key={`${rowName}-${colName}`} className="border-b border-gray-100 px-2 py-1 text-center text-[10px] text-gray-400">N/A</td>
                                );
                              }
                              const grade = gradeFromValue(info.time_decay_weight, thresholds);
                              const cls = gradeColor(grade);
                              const anchorKey = `${rowName}-${colName}`;
                              const lines = [
                                `총 ${info.count}회 만남`,
                                ...(Array.isArray(info.occurrence_dates) && info.occurrence_dates.length > 0
                                  ? info.occurrence_dates.map(d => {
                                      try {
                                        const dt = new Date(d);
                                        return dt.toLocaleDateString('ko-KR');
                                      } catch (e) { return d; }
                                    })
                                  : ['기록 없음'])
                              ];
                              return (
                                <td key={`${rowName}-${colName}`} className="border-b border-gray-100 px-2 py-1 text-center whitespace-nowrap">
                                  <button
                                    type="button"
                                    onClick={(e) => openPopover(e, `${rowName} · ${colName}`, lines, anchorKey)}
                                    className={`inline-block min-w-[24px] px-1 rounded ${cls} hover:opacity-90 focus:outline-none`}
                                  >
                                    {grade}
                                  </button>
                                </td>
                              );
                            })}
                          </tr>
                        ));
                      })()}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            <div className="mt-3 text-xs text-gray-500">
              <p>등급은 현재 참석자들 간의 과거 만남 빈도를 4단계로 나눈 상대적 기준입니다.</p>
            </div>
          </div>
        )}

        {/* 팝오버: 자연스러운 카드형 오버레이 */}
        {popover.show && (
          popover.isMobile ? (
            <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center">
              <div className="absolute inset-0 bg-black bg-opacity-30" onClick={closePopover}></div>
              <div className="relative bg-white w-full md:w-80 rounded-t-lg md:rounded-lg shadow-xl border border-gray-200">
                <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                  <div className="text-sm font-semibold text-gray-800 truncate">{popover.title}</div>
                  <button onClick={closePopover} className="text-gray-400 hover:text-gray-600 text-sm">✕</button>
                </div>
                <div className="p-4 max-h-[60vh] overflow-auto">
                  <ul className="text-sm text-gray-700 space-y-1 list-disc pl-5">
                    {popover.lines.map((line, idx) => (
                      <li key={`${popover.anchorKey}-${idx}`}>{line}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div
              className="absolute z-50"
              style={{ left: popover.x, top: popover.y, transform: 'translateX(-50%)' }}
            >
              <div className="bg-white shadow-lg rounded-md border border-gray-200 w-64">
                <div className="px-3 py-2 border-b border-gray-100 flex items-center justify-between">
                  <div className="text-xs font-semibold text-gray-800 truncate">{popover.title}</div>
                  <button onClick={closePopover} className="text-gray-400 hover:text-gray-600 text-xs">✕</button>
                </div>
                <div className="p-3 max-h-56 overflow-auto">
                  <ul className="text-xs text-gray-700 space-y-1 list-disc pl-4">
                    {popover.lines.map((line, idx) => (
                      <li key={`${popover.anchorKey}-${idx}`}>{line}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )
        )}

        {/* 조 생성 기록 */}
        {view === 'history' && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-lg font-semibold">조 생성 기록</h2>
            </div>

            {loadingHistory ? (
              <div className="flex justify-center items-center py-8">
                <svg className="animate-spin h-8 w-8 text-indigo-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
            ) : teamHistory.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <p>저장된 조 생성 기록이 없습니다.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {teamHistory.slice().reverse().map((historyItem) => (
                  <div key={historyItem.date} className="border border-gray-200 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-4 py-2 flex flex-col sm:flex-row justify-between items-start sm:items-center">
                      <div className="mb-2 sm:mb-0">
                        <span className="text-sm font-medium text-gray-900">
                          {formatDateTime(historyItem.date)}
                        </span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {historyItem.method_used === 'simulated_annealing' ? '최적화' : '랜덤'}
                          </span>
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            참가자 {historyItem.participants_count}명
                          </span>
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                            λ={historyItem.lambda_value}
                          </span>
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                            조 {historyItem.groups.length}개
                          </span>
                        </div>
                      </div>
                      <div className="flex flex-col space-y-1 sm:flex-row sm:space-y-0 sm:space-x-2 w-full sm:w-auto">
                        <button
                          onClick={() => loadHistoryTeam(historyItem)}
                          className="inline-flex items-center justify-center px-2 py-1 border border-indigo-300 text-xs font-medium rounded-md text-indigo-700 bg-white hover:bg-indigo-50 w-full sm:w-auto"
                        >
                          자세한 정보 보기
                        </button>
                        <button
                          onClick={() => setDeleteConfirmDate(historyItem.date)}
                          className="inline-flex items-center justify-center px-2 py-1 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-white hover:bg-red-50 w-full sm:w-auto"
                        >
                          삭제
                        </button>
                      </div>
                    </div>
                    <div className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        {historyItem.groups.map((group, idx) => (
                          <div key={idx} className="border border-gray-200 rounded-md px-2 py-1 text-xs">
                            <div className="font-medium text-gray-900 mb-1">조 {idx + 1}</div>
                            <div className="text-gray-600">
                              {group.join(', ')}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {showConfirmPopup && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 shadow-xl max-w-md w-full">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                확인해주세요
              </h3>
              <p className="text-sm text-gray-500 mb-6">
                {latestTodayTimeText || '엇, 오늘 이미 조를 짜셨네요! 추가로 한 번 더 만드시겠어요?'}
              </p>
              <div className="flex flex-col space-y-3">
                <button
                  onClick={() => generateTeamsExecute(true)}
                  className="inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  네, 추가로 만들게요
                </button>
                <button
                  onClick={() => setShowConfirmPopup(false)}
                  className="inline-flex justify-center items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  아뇨, 괜찮아요
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 삭제 확인 팝업 */}
        {deleteConfirmDate && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 shadow-xl max-w-md w-full">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                기록 삭제 확인
              </h3>
              <p className="text-sm text-gray-500 mb-6">
                {deleteConfirmDate === 'all' 
                  ? '모든 조 생성 기록을 삭제하시겠습니까?' 
                  : `${formatDateTime(deleteConfirmDate)} 기록을 삭제하시겠습니까?`}
              </p>
              <div className="flex flex-row-reverse space-x-2 space-x-reverse">
                <button
                  onClick={() => deleteConfirmDate === 'all' ? deleteAllTeamHistory() : deleteTeamHistory(deleteConfirmDate)}
                  className="inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  삭제
                </button>
                <button
                  onClick={() => setDeleteConfirmDate(null)}
                  className="inline-flex justify-center items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  취소
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 참가자 삭제 확인 팝업 */}
        {deleteParticipantName && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 shadow-xl max-w-md w-full">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                참가자 삭제 확인
              </h3>
              <p className="text-sm text-gray-500 mb-6">
                {`${deleteParticipantName}을(를) 삭제할까요?`}
              </p>
              <div className="flex flex-row-reverse space-x-2 space-x-reverse">
                <button
                  onClick={() => { removeParticipant(deleteParticipantName); setDeleteParticipantName(null); }}
                  className="inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  삭제
                </button>
                <button
                  onClick={() => setDeleteParticipantName(null)}
                  className="inline-flex justify-center items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  취소
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

