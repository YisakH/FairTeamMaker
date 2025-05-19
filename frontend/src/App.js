import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { PlusIcon, TrashIcon, UserGroupIcon, CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';
import NaverLogin from './components/auth/NaverLogin';
import { useAuth } from './components/auth/AuthContext';

// API 기본 URL을 환경변수에서 가져오거나 기본값으로 localhost 사용
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const { user, isAuthenticated, login, logout } = useAuth();
  const [participants, setParticipants] = useState([]);
  const [attendingParticipants, setAttendingParticipants] = useState([]);
  const [newParticipant, setNewParticipant] = useState('');
  const [groups, setGroups] = useState([]);
  const [cooccurrenceInfo, setCooccurrenceInfo] = useState({});
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('manage'); // 'manage', 'attendance', 'options', 'results', 'history'
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

  // 시뮬레이티드 어닐링 파라미터
  const [saParams, setSaParams] = useState({
    initial_temp: 100.0,
    cooling_rate: 0.995,
    temp_min: 0.1,
    max_iter: 5000
  });

  useEffect(() => {
    fetchParticipants();
    fetchAttendingParticipants();
    fetchCooccurrenceInfo();
  }, []);

  // 람다값이 변경되면 cooccurrence 정보 다시 불러오기
  useEffect(() => {
    fetchCooccurrenceInfo();
  }, [lambdaValue]);

  const fetchParticipants = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/participants`);
      setParticipants(response.data);
    } catch (error) {
      console.error('참가자 목록을 불러오는데 실패했습니다:', error);
    }
  };

  const fetchAttendingParticipants = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/attending`);
      setAttendingParticipants(response.data);
    } catch (error) {
      console.error('참석자 목록을 불러오는데 실패했습니다:', error);
    }
  };

  const fetchCooccurrenceInfo = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/cooccurrence`, {
        params: { lam: lambdaValue }
      });
      setCooccurrenceInfo(response.data);
    } catch (error) {
      console.error('공동 참여 정보를 불러오는데 실패했습니다:', error);
    }
  };

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
      
      if (exists) {
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
      const response = await axios.get(`${API_BASE_URL}/team-history`);
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
    setView('results');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-3xl font-bold text-gray-900">조 생성기</h1>
          <div className="flex items-center space-x-4">
            {isAuthenticated() ? (
              <div className="flex items-center">
                <span className="text-sm font-medium text-gray-700 mr-2">
                  {user?.name}님 환영합니다
                </span>
                <button
                  onClick={logout}
                  className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-1 focus:ring-offset-1 focus:ring-red-500"
                >
                  로그아웃
                </button>
              </div>
            ) : (
              <NaverLogin onLoginSuccess={login} />
            )}
          </div>
        </div>

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
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setView('attendance')}
              className={`${view === 'attendance' 
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              참석 여부 관리
            </button>
            <button
              onClick={() => setView('manage')}
              className={`${view === 'manage' 
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              참가자 관리
            </button>
            <button
              onClick={() => {
                setView('history');
                fetchTeamHistory();
              }}
              className={`${view === 'history' 
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              조 기록 보기
            </button>
            {groups.length > 0 && (
              <button
                onClick={() => setView('results')}
                className={`${view === 'results' 
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                결과 보기
              </button>
            )}
            <button
              onClick={() => setView('options')}
              className={`${view === 'options' 
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              조 생성 옵션
            </button>
          </nav>
        </div>

        {view === 'manage' && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <h2 className="text-lg font-semibold mb-3">참가자 관리</h2>
            <form onSubmit={addParticipant} className="flex gap-2">
              <input
                type="text"
                value={newParticipant}
                onChange={(e) => setNewParticipant(e.target.value)}
                placeholder="새 참가자 이름"
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

            {/* 참가자 목록 - 더 콤팩트하게 변경 */}
            <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-2">
              {participants.map((name) => (
                <div
                  key={name}
                  className="flex items-center justify-between bg-gray-50 rounded-md px-2 py-1.5 text-xs"
                >
                  <span className="font-medium text-gray-900 truncate mr-1">{name}</span>
                  <button
                    onClick={() => removeParticipant(name)}
                    className="text-gray-400 hover:text-red-500 flex-shrink-0"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {view === 'attendance' && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-lg font-semibold">조 짜기 반영 여부</h2>
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

            {/* 모바일 최적화: 그리드를 2열 또는 3열로 설정하고 참가자 카드를 콤팩트하게 변경 */}
            <div className="mt-2 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-2">
              {participants.map((name) => (
                <div
                  key={name}
                  className={`border rounded-md px-2 py-1.5 ${isAttending(name) ? 'border-green-500 bg-green-50' : 'border-gray-300'}`}
                >
                  <label className="flex items-center justify-between cursor-pointer w-full">
                    <span className={`text-xs font-medium truncate mr-1 ${isAttending(name) ? 'text-green-900' : 'text-gray-700'}`}>
                      {name}
                    </span>
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
                  </label>
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
              <h2 className="text-lg font-semibold mb-3">조 구성</h2>
              
              <div className="mb-3 p-2 bg-gray-50 rounded-md text-xs">
                <div className="grid grid-cols-2 gap-1">
                  <div className="flex items-center">
                    <span className="inline-block w-2 h-2 rounded-full bg-green-600 mr-1"></span>
                    <span>0: 없음</span>
                  </div>
                  <div className="flex items-center">
                    <span className="inline-block w-2 h-2 rounded-full bg-blue-600 mr-1"></span>
                    <span>25: 1회</span>
                  </div>
                  <div className="flex items-center">
                    <span className="inline-block w-2 h-2 rounded-full bg-yellow-600 mr-1"></span>
                    <span>50: 2회</span>
                  </div>
                  <div className="flex items-center">
                    <span className="inline-block w-2 h-2 rounded-full bg-red-600 mr-1"></span>
                    <span>75-95: 3회 이상</span>
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
                      
                      {/* 상세 정보 토글 (모바일에서 더 콤팩트하게) */}
                      <div className="mt-1 border-t border-gray-200 pt-2">
                        <details className="text-xs text-gray-600">
                          <summary className="font-medium cursor-pointer hover:text-indigo-600 flex items-center">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                            </svg>
                            상세 정보 보기
                          </summary>
                          <div className="mt-2 space-y-2">
                            {group.map((member) => (
                              <div key={member} className="bg-white rounded-md p-2 shadow-sm">
                                <div className="font-medium text-gray-900 mb-1 text-xs">{member}와(과) 같은 조 이력</div>
                                <div className="text-xs text-gray-500 space-y-1">
                                  {group.map((other) => {
                                    if (other === member) return null;
                                    const info = cooccurrenceInfo[member]?.[other];
                                    if (!info) return null;
                                    
                                    // 조 구성 횟수에 따라 직접 점수 계산 (직관적인 방식)
                                    let avoidScore;
                                    if (info.count === 1) avoidScore = 25;
                                    else if (info.count === 2) avoidScore = 50;
                                    else if (info.count === 3) avoidScore = 75;
                                    else if (info.count >= 4) avoidScore = 95;
                                    else avoidScore = 0;
                                    
                                    let scoreColor = "text-green-600";
                                    
                                    if (avoidScore > 70) {
                                      scoreColor = "text-red-600";
                                    } else if (avoidScore > 40) {
                                      scoreColor = "text-yellow-600";
                                    } else if (avoidScore > 20) {
                                      scoreColor = "text-blue-600";
                                    }
                                    
                                    let lastMet = "";
                                    if (info.last_occurrence) {
                                      try {
                                        const lastDate = new Date(info.last_occurrence);
                                        lastMet = `, 마지막: ${lastDate.toLocaleDateString('ko-KR')}`;
                                      } catch (e) {}
                                    }
                                    
                                    return (
                                      <div key={other} className="flex justify-between items-center py-1 border-b border-gray-100">
                                        <span>{other}</span>
                                        <span>
                                          <span className="mr-1">{info.count}회</span>
                                          <span className={scoreColor}>
                                            ({avoidScore})
                                          </span>
                                        </span>
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

        {/* 조 생성 기록 */}
        {view === 'history' && (
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-lg font-semibold">조 생성 기록</h2>
              <div className="flex space-x-2">
                <button
                  onClick={() => deleteTodayData()}
                  className="inline-flex items-center px-2 py-1 border border-orange-300 text-xs font-medium rounded-md text-orange-700 bg-white hover:bg-orange-50"
                  disabled={teamHistory.length === 0}
                >
                  오늘 중복 데이터 정리
                </button>
                <button
                  onClick={() => setDeleteConfirmDate('all')}
                  className="inline-flex items-center px-2 py-1 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                  disabled={teamHistory.length === 0}
                >
                  전체 기록 삭제
                </button>
              </div>
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
                    <div className="bg-gray-50 px-4 py-2 flex justify-between items-center">
                      <div>
                        <span className="text-sm font-medium text-gray-900">
                          {formatDateTime(historyItem.date)}
                        </span>
                        <div className="flex space-x-2 mt-1">
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
                      <div className="flex space-x-2">
                        <button
                          onClick={() => loadHistoryTeam(historyItem)}
                          className="inline-flex items-center px-2 py-1 border border-indigo-300 text-xs font-medium rounded-md text-indigo-700 bg-white hover:bg-indigo-50"
                        >
                          보기
                        </button>
                        <button
                          onClick={() => setDeleteConfirmDate(historyItem.date)}
                          className="inline-flex items-center px-2 py-1 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
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
                오늘 이미 생성된 조 데이터가 있습니다
              </h3>
              <p className="text-sm text-gray-500 mb-6">
                오늘 날짜에 이미 만들어진 조 데이터가 있습니다. 어떻게 하시겠습니까?
              </p>
              <div className="flex flex-col space-y-3">
                <button
                  onClick={() => generateTeamsExecute(true)}
                  className="inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  오늘 기존 조 데이터 유지하고 추가 생성하기
                  <span className="block ml-2 text-xs opacity-80">(하루에 여러 번 조 구성이 필요한 경우)</span>
                </button>
                <button
                  onClick={() => generateTeamsExecute(false)}
                  className="inline-flex justify-center items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  오늘 기존 조 데이터 삭제하고 새로 만들기
                  <span className="block ml-2 text-xs opacity-80">(실수로 팀을 잘못 짰거나 다시 짜고 싶은 경우)</span>
                </button>
                <button
                  onClick={() => setShowConfirmPopup(false)}
                  className="inline-flex justify-center items-center px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700"
                >
                  취소
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
      </div>
    </div>
  );
}

export default App;
