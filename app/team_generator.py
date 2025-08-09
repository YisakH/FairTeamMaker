import random
import math
import json
from datetime import date, timedelta, datetime
from typing import List, Dict, Tuple

class TeamGenerator:
    def __init__(self, team_history_file: str = "data/team_history.json"):
        self.team_history_file = team_history_file
        self.past_dates: Dict[str, Dict[str, List[str]]] = {}
        self.base_date: date = None  # 기준 날짜 (Week 1)
        
        # 시간 감쇠 파라미터
        self.decay_rate = 0.6  # 시간 감쇠율 (0~1, 낮을수록 빠르게 감쇠)
        self.frequency_weight = 0.6  # 빈도 가중치 (A)
        self.recency_weight = 0.4    # 최근성 가중치 (B)
        self.first_meeting_bonus = -0.5  # 첫 만남 보너스 (음수 = 선호)
        self.base_penalty = 1.0      # 기본 페널티

    def load_past_cooccurrence_from_history(self, participants: List[str]) -> None:
        """Load past co-occurrence data from team history with time decay consideration."""
        try:
            with open(self.team_history_file, "r", encoding='utf-8') as f:
                history = json.load(f)
                print(f"[디버깅] 팀 히스토리에서 데이터 로드 성공: {self.team_history_file}")
                print(f"[디버깅] 히스토리 기록 수: {len(history)}")
        except FileNotFoundError:
            print(f"[디버깅] 파일이 존재하지 않음: {self.team_history_file}")
            history = []
        except json.JSONDecodeError:
            print(f"[디버깅] JSON 파싱 오류: {self.team_history_file}")
            history = []

        # 기준 날짜 설정 (가장 오래된 기록을 Week 1로)
        if history:
            dates = []
            for record in history:
                record_date_str = record['date'][:10]
                dates.append(datetime.fromisoformat(record_date_str).date())
            dates.sort()
            self.base_date = dates[0]
            print(f"[디버깅] 기준 날짜 설정 (Week 1): {self.base_date}")
        else:
            self.base_date = date.today()
            print(f"[디버깅] 기록이 없어 현재 날짜를 기준으로 설정: {self.base_date}")

        # 참가자별 공동 참여 데이터 초기화
        self.past_dates = {}
        for p in participants:
            self.past_dates[p] = {}
            for q in participants:
                if p != q:
                    self.past_dates[p][q] = []

        # 팀 히스토리에서 공동 참여 데이터 생성 (모든 기록 사용, 윈도우 제한 없음)
        valid_records = 0
        for record in history:
            try:
                record_date_str = record['date'][:10]
                valid_records += 1
                # 각 그룹 내의 모든 참가자 쌍에 대해 공동 참여 기록
                for group in record['groups']:
                    for i in range(len(group)):
                        for j in range(len(group)):
                            if i != j and group[i] in participants and group[j] in participants:
                                if group[i] in self.past_dates and group[j] in self.past_dates[group[i]]:
                                    self.past_dates[group[i]][group[j]].append(record_date_str)
            except (KeyError, ValueError, TypeError) as e:
                print(f"[디버깅] 기록 처리 중 오류: {e}")
                continue

        print(f"[디버깅] 처리된 기록 수: {valid_records}")
        print(f"[디버깅] 생성된 공동 참여 데이터 참가자 수: {len(self.past_dates)}")

    def _get_current_week(self) -> int:
        """현재 주차를 계산 (기준 날짜로부터)"""
        if self.base_date is None:
            return 1
        today = date.today()
        days_from_base = (today - self.base_date).days
        return (days_from_base // 7) + 1

    def _get_week_from_date(self, date_str: str) -> int:
        """날짜 문자열에서 주차 계산"""
        if self.base_date is None:
            return 1
        target_date = datetime.fromisoformat(date_str).date()
        days_from_base = (target_date - self.base_date).days
        return (days_from_base // 7) + 1

    def _calculate_time_decay_weight(self, p1: str, p2: str) -> float:
        """시간 감쇠를 적용한 가중치 계산"""
        dates = self.past_dates.get(p1, {}).get(p2, [])
        
        if not dates:
            # 한 번도 만난 적 없음 → 첫 만남 보너스
            return self.first_meeting_bonus
        
        current_week = self._get_current_week()
        
        # 빈도 점수: 총 만난 횟수 기반
        total_meetings = len(dates)
        frequency_score = math.exp(-0.7 * total_meetings)  # 기존 방식 유지
        
        # 최근성 점수: 마지막 만남으로부터의 시간 감쇠
        last_meeting_date = max(dates)
        last_meeting_week = self._get_week_from_date(last_meeting_date)
        weeks_ago = current_week - last_meeting_week
        
        if weeks_ago <= 0:
            # 이번 주 또는 미래 (이론적으로 불가능하지만 안전장치)
            recency_score = self.base_penalty
        else:
            recency_score = self.base_penalty * (self.decay_rate ** weeks_ago)
        
        # 최종 가중치: 빈도와 최근성의 가중합
        final_weight = (self.frequency_weight * frequency_score) + (self.recency_weight * recency_score)
        
        return final_weight

    def get_cooccurrence_info(self, participants: List[str], lam: float = 0.7) -> Dict[str, Dict[str, Dict]]:
        """Get detailed co-occurrence information for all pairs with time decay."""
        info = {}
        current_week = self._get_current_week()
        
        for p in participants:
            info[p] = {}
            for q in participants:
                if p == q:
                    continue
                    
                dates = self.past_dates.get(p, {}).get(q, [])
                count = len(dates)
                last_occurrence = max(dates) if dates else None
                
                # 시간 감쇠 적용 가중치 계산
                weight = self._calculate_time_decay_weight(p, q)
                
                # 추가 정보: 마지막 만남 주차
                last_week = None
                weeks_ago = None
                if last_occurrence:
                    last_week = self._get_week_from_date(last_occurrence)
                    weeks_ago = current_week - last_week
                
                info[p][q] = {
                    "count": count,
                    "probability": math.exp(-weight) if weight >= 0 else math.exp(weight),  # 가중치 기반 확률
                    "last_occurrence": last_occurrence,
                    "last_week": last_week,
                    "weeks_ago": weeks_ago,
                    "time_decay_weight": weight
                }
        return info

    def generate_groups(self, participants: List[str], lam: float = 3.0) -> List[List[str]]:
        """
        Generate optimized groups using simulated annealing with time decay weights.
        """
        # 참가자 수가 너무 적으면 기존 방식으로 처리
        if len(participants) < 8:
            return self._generate_groups_weighted_random(participants, lam)
            
        # 시간 감쇠 기반 가중치 딕셔너리 생성
        time_decay_weights = self._get_time_decay_weights(participants)
        
        # 시뮬레이티드 어닐링 알고리즘으로 최적화
        return self._simulated_annealing(participants, time_decay_weights, lam)

    def _generate_groups_weighted_random(self, participants: List[str], lam: float = 3.0) -> List[List[str]]:
        """
        Group generation using weighted random selection with time decay.
        """
        n = len(participants)
        sizes = self._partition_group_sizes(n)
        random.shuffle(sizes)

        remaining = participants.copy()
        groups: List[List[str]] = []

        for size in sizes:
            leader = random.choice(remaining)
            group = [leader]
            remaining.remove(leader)

            while len(group) < size:
                weights = []
                for cand in remaining:
                    # 그룹 내 모든 멤버와의 시간 감쇠 가중치 합계
                    total_weight = sum(self._calculate_time_decay_weight(mem, cand) for mem in group)
                    # 가중치가 음수(첫 만남 보너스)인 경우를 고려하여 확률 계산
                    if total_weight < 0:
                        weights.append(math.exp(-total_weight))  # 음수를 양수로 변환하여 높은 확률
                    else:
                        weights.append(math.exp(-lam * total_weight))
                
                chosen = random.choices(remaining, weights=weights, k=1)[0]
                group.append(chosen)
                remaining.remove(chosen)

            groups.append(group)

        return groups

    def _get_time_decay_weights(self, participants: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Generate a dictionary of time decay weights for all participant pairs.
        """
        weights = {}
        for p in participants:
            weights[p] = {}
            for q in participants:
                if p == q:
                    continue
                weights[p][q] = self._calculate_time_decay_weight(p, q)
        return weights

    def _initial_partition(self, participants: List[str]) -> List[List[str]]:
        """
        Create an initial random partition of participants into groups.
        """
        sizes = self._partition_group_sizes(len(participants))
        shuffled = participants.copy()
        random.shuffle(shuffled)
        
        groups = []
        idx = 0
        for size in sizes:
            groups.append(shuffled[idx:idx+size])
            idx += size
        return groups

    def _group_cost(self, group: List[str], weights: Dict[str, Dict[str, float]], lam: float) -> float:
        """
        Compute the cost of a group based on time decay weights.
        """
        cost = 0.0
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                p1, p2 = group[i], group[j]
                weight = weights.get(p1, {}).get(p2, 0)
                # 첫 만남 보너스(음수)를 포함하여 처리
                if weight < 0:
                    cost += weight  # 음수 가중치는 비용을 감소시킴 (좋은 것)
                else:
                    cost += (1 - math.exp(-lam * weight))
        return cost

    def _total_cost(self, groups: List[List[str]], weights: Dict[str, Dict[str, float]], lam: float) -> float:
        """
        Compute the total cost for all groups.
        """
        return sum(self._group_cost(g, weights, lam) for g in groups)

    def _neighbor_partition(self, groups: List[List[str]]) -> Tuple[List[List[str]], Tuple[int, int, int, int]]:
        """
        Generate a neighbor solution by swapping two participants in different groups.
        """
        new_groups = [g.copy() for g in groups]
        # 두 개의 다른 그룹 선택
        g1, g2 = random.sample(range(len(groups)), 2)
        # 각 그룹에서 무작위 멤버 선택
        i1 = random.randrange(len(new_groups[g1]))
        i2 = random.randrange(len(new_groups[g2]))
        # 교환
        new_groups[g1][i1], new_groups[g2][i2] = new_groups[g2][i2], new_groups[g1][i1]
        return new_groups, (g1, i1, g2, i2)

    def _simulated_annealing(
        self,
        participants: List[str],
        weights: Dict[str, Dict[str, float]],
        lam: float = 3.0,
        initial_temp: float = 100.0,
        cooling_rate: float = 0.995,
        temp_min: float = 0.1,
        max_iter: int = 1000
    ) -> List[List[str]]:
        """
        Optimize the partition using simulated annealing algorithm with time decay weights.
        """
        current = self._initial_partition(participants)
        best = current
        current_cost = self._total_cost(current, weights, lam)
        best_cost = current_cost
        T = initial_temp
        
        print(f"[디버깅] 시뮬레이티드 어닐링 시작 - 초기 비용: {current_cost:.4f}")
        
        for it in range(max_iter):
            if T < temp_min:
                break
                
            candidate, swap_info = self._neighbor_partition(current)
            cand_cost = self._total_cost(candidate, weights, lam)
            delta = cand_cost - current_cost
            
            # 더 좋은 솔루션이거나 확률적으로 수락
            if delta < 0 or random.random() < math.exp(-delta / T):
                current = candidate
                current_cost = cand_cost
                
                # 지금까지의 최선의 솔루션 갱신
                if cand_cost < best_cost:
                    best = candidate
                    best_cost = cand_cost
            
            # 온도 감소
            T *= cooling_rate
        
        print(f"[디버깅] 시뮬레이티드 어닐링 완료 - 최종 비용: {best_cost:.4f}")
        return best

    @staticmethod
    def _partition_group_sizes(n: int) -> List[int]:
        """Divide n participants into groups of 4 or 5."""
        r = n % 4
        num_fives = r
        num_fours = (n - 5 * r) // 4
        return [5] * num_fives + [4] * num_fours