import random
import math
import json
from datetime import date, timedelta, datetime
from typing import List, Dict, Tuple

class TeamGenerator:
    def __init__(self, team_history_file: str = "data/team_history.json"):
        self.team_history_file = team_history_file
        self.past_dates: Dict[str, Dict[str, List[str]]] = {}

    def load_past_cooccurrence_from_history(self, participants: List[str], window_days: int = 60) -> None:
        """Load past co-occurrence data from team history and prune old data."""
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

        today = date.today()
        cutoff = today - timedelta(days=window_days)
        print(f"[디버깅] 날짜 범위: {cutoff} ~ {today}")

        # 참가자별 공동 참여 데이터 초기화
        self.past_dates = {}
        for p in participants:
            self.past_dates[p] = {}
            for q in participants:
                if p != q:
                    self.past_dates[p][q] = []

        # 팀 히스토리에서 공동 참여 데이터 생성
        valid_records = 0
        for record in history:
            try:
                # 날짜 파싱 (ISO 형식에서 날짜 부분만 추출)
                record_date_str = record['date'][:10]  # "2025-06-01T10:36:27.121908" -> "2025-06-01"
                record_date = date.fromisoformat(record_date_str)
                
                # 날짜 범위 확인
                if record_date >= cutoff:
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

        print(f"[디버깅] 유효한 기록 수: {valid_records}")
        print(f"[디버깅] 생성된 공동 참여 데이터 참가자 수: {len(self.past_dates)}")

    def get_cooccurrence_info(self, participants: List[str], lam: float = 0.7) -> Dict[str, Dict[str, Dict]]:
        """Get detailed co-occurrence information for all pairs."""
        info = {}
        for p in participants:
            info[p] = {}
            for q in participants:
                if p == q:
                    continue
                dates = self.past_dates.get(p, {}).get(q, [])
                count = len(dates)
                last_occurrence = max(dates) if dates else None
                
                # Calculate probability based on exponential decay
                probability = math.exp(-lam * count)  # Using provided lambda value
                
                info[p][q] = {
                    "count": count,
                    "probability": probability,
                    "last_occurrence": last_occurrence
                }
        return info

    def generate_groups(self, participants: List[str], lam: float = 3.0) -> List[List[str]]:
        """
        Generate optimized groups using simulated annealing.
        This method replaces the old weighted random selection method.
        """
        # 참가자 수가 너무 적으면 기존 방식으로 처리
        if len(participants) < 8:
            return self._generate_groups_weighted_random(participants, lam)
            
        # 공동 참여 횟수 딕셔너리 생성
        cooccurrence_counts = self._get_cooccurrence_counts(participants)
        
        # 시뮬레이티드 어닐링 알고리즘으로 최적화
        return self._simulated_annealing(participants, cooccurrence_counts, lam)

    def _generate_groups_weighted_random(self, participants: List[str], lam: float = 3.0) -> List[List[str]]:
        """
        Original group generation method using weighted random selection.
        Keep this as a fallback for small participant counts.
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
                    cnt = sum(len(self.past_dates.get(mem, {}).get(cand, [])) for mem in group)
                    weights.append(math.exp(-lam * cnt))
                chosen = random.choices(remaining, weights=weights, k=1)[0]
                group.append(chosen)
                remaining.remove(chosen)

            groups.append(group)

        return groups

    def _get_cooccurrence_counts(self, participants: List[str]) -> Dict[str, Dict[str, int]]:
        """
        Generate a dictionary of co-occurrence counts for all participant pairs.
        """
        counts = {}
        for p in participants:
            counts[p] = {}
            for q in participants:
                if p == q:
                    continue
                dates = self.past_dates.get(p, {}).get(q, [])
                counts[p][q] = len(dates)
        return counts

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

    def _group_cost(self, group: List[str], counts: Dict[str, Dict[str, int]], lam: float) -> float:
        """
        Compute the cost of a group based on co-occurrence counts.
        Higher counts result in higher costs.
        """
        cost = 0.0
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                p1, p2 = group[i], group[j]
                count = counts.get(p1, {}).get(p2, 0)
                # 지수 함수로 가중치 적용 (count가 높을수록 비용이 급격히 증가)
                cost += (1 - math.exp(-lam * count))
        return cost

    def _total_cost(self, groups: List[List[str]], counts: Dict[str, Dict[str, int]], lam: float) -> float:
        """
        Compute the total cost for all groups.
        """
        return sum(self._group_cost(g, counts, lam) for g in groups)

    def _neighbor_partition(self, groups: List[List[str]]) -> Tuple[List[List[str]], Tuple[int, int, int, int]]:
        """
        Generate a neighbor solution by swapping two participants in different groups.
        Returns new groups and the swap indices ((g1, i1), (g2, i2)).
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
        counts: Dict[str, Dict[str, int]],
        lam: float = 3.0,
        initial_temp: float = 100.0,
        cooling_rate: float = 0.995,
        temp_min: float = 0.1,
        max_iter: int = 5000
    ) -> List[List[str]]:
        """
        Optimize the partition using simulated annealing algorithm.
        """
        current = self._initial_partition(participants)
        best = current
        current_cost = self._total_cost(current, counts, lam)
        best_cost = current_cost
        T = initial_temp
        
        for it in range(max_iter):
            if T < temp_min:
                break
                
            candidate, swap_info = self._neighbor_partition(current)
            cand_cost = self._total_cost(candidate, counts, lam)
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
        
        return best

    @staticmethod
    def _partition_group_sizes(n: int) -> List[int]:
        """Divide n participants into groups of 4 or 5."""
        r = n % 4
        num_fives = r
        num_fours = (n - 5 * r) // 4
        return [5] * num_fives + [4] * num_fours