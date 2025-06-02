import random
import math
import json
from datetime import date, timedelta
from typing import List, Dict, Tuple

class TeamGenerator:
    def __init__(self, data_file: str = "data/past_cooccurrence.json"):
        self.data_file = data_file
        self.past_dates: Dict[str, Dict[str, List[str]]] = {}

    def load_past_cooccurrence(self, participants: List[str], window_days: int = 60) -> None:
        """Load and prune past co-occurrence data."""
        try:
            with open(self.data_file, "r", encoding='utf-8') as f:
                data = json.load(f)
                print(f"[디버깅] 파일에서 데이터 로드 성공: {self.data_file}")
                print(f"[디버깅] 로드된 데이터 크기: {len(data)}")
        except FileNotFoundError:
            print(f"[디버깅] 파일이 존재하지 않음: {self.data_file}")
            data = {}
        except json.JSONDecodeError:
            print(f"[디버깅] JSON 파싱 오류: {self.data_file}")
            data = {}

        today = date.today()
        cutoff = today - timedelta(days=window_days)
        print(f"[디버깅] 날짜 범위: {cutoff} ~ {today}")

        # 참가자 데이터 상태 확인
        new_participants = [p for p in participants if p not in data]
        if new_participants:
            print(f"[디버깅] 새로 추가된 참가자들: {new_participants}")
            
        # 원본 데이터 복사 (중요: 전체 데이터를 유지)
        self.past_dates = data.copy()

        # 새로운 참가자에 대한 데이터 구조 생성 (기존 데이터는 유지)
        for p in participants:
            if p not in self.past_dates:
                self.past_dates[p] = {}
            
            for q in participants:
                if p == q:
                    continue
                if q not in self.past_dates[p]:
                    self.past_dates[p][q] = []
                    
        # 오래된 날짜 데이터 정리 (prune)
        for p in list(self.past_dates.keys()):
            for q in list(self.past_dates.get(p, {}).keys()):
                raw = self.past_dates[p].get(q, [])
                
                # Backward compatibility: if int, create that many dates at cutoff
                if isinstance(raw, int):
                    dates = [cutoff.isoformat()] * raw
                elif isinstance(raw, list):
                    dates = raw
                else:
                    dates = []

                # Prune old dates
                valid = []
                for ds in dates:
                    try:
                        d = date.fromisoformat(ds)
                        if d >= cutoff:
                            valid.append(ds)
                    except ValueError:
                        continue
                self.past_dates[p][q] = valid

        print(f"[디버깅] 처리 후 데이터 크기: {len(self.past_dates)}")

    def save_past_cooccurrence(self) -> None:
        """Save the current state to JSON file."""
        print(f"[디버깅] 저장 전 데이터 상태: {len(self.past_dates)} 참가자")
        
        # 날짜별 카운트
        date_counts = {}
        total_entries = 0
        for p in self.past_dates:
            for q in self.past_dates[p]:
                for d in self.past_dates[p][q]:
                    date_counts[d] = date_counts.get(d, 0) + 1
                    total_entries += 1
        
        print(f"[디버깅] 총 데이터 항목 수: {total_entries}")
        print(f"[디버깅] 날짜별 데이터 수: {date_counts}")
        
        with open(self.data_file, "w", encoding='utf-8') as f:
            json.dump(self.past_dates, f, indent=2, ensure_ascii=False)
            print(f"[디버깅] 데이터 저장 완료: {self.data_file}")

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

    def update_cooccurrence(self, groups: List[List[str]], accumulate_same_day: bool = True) -> None:
        """
        Update co-occurrence data with new groups.
        
        Args:
            groups: List of participant groups
            accumulate_same_day: If False (default), removes existing entries for today before adding new ones
                                 If True, accumulates multiple entries for the same day
        """
        today_str = date.today().isoformat()
        
        # 디버깅을 위해 처리 전 상태 출력
        print(f"[디버깅] 오늘 날짜: {today_str}")
        print(f"[디버깅] 전체 참가자 데이터 개수: {len(self.past_dates)}")
        print(f"[디버깅] accumulate_same_day 설정: {accumulate_same_day}")
        
        # 현재 참가자 목록 수집
        participants_in_groups = set()
        for grp in groups:
            for p in grp:
                participants_in_groups.add(p)
        
        # 해당 날짜의 데이터 카운트
        today_count_before = 0
        for p in self.past_dates:
            for q in self.past_dates.get(p, {}):
                if q in self.past_dates[p]:
                    today_count_before += self.past_dates[p][q].count(today_str)
        print(f"[디버깅] 삭제 전 오늘 날짜 기록 수: {today_count_before}")
        
        # 같은 날짜 누적을 방지하기 위해 오늘 날짜의 기존 데이터 제거
        if not accumulate_same_day:
            # 최신 데이터를 찾기 위해 각 참가자 쌍별로 최신 등록 시간 찾기
            latest_additions = {}
            
            # 1. 먼저 각 참가자 쌍별로 오늘 날짜 데이터 수집
            for p in participants_in_groups:
                if p not in self.past_dates:
                    continue
                
                for q in participants_in_groups:
                    if p == q or q not in self.past_dates[p]:
                        continue
                    
                    # 오늘 날짜 데이터 찾기
                    today_dates = [d for d in self.past_dates[p][q] if d == today_str]
                    
                    # 오늘 데이터가 있는 경우
                    if today_dates:
                        pair_key = tuple(sorted([p, q]))
                        if pair_key not in latest_additions:
                            latest_additions[pair_key] = 0
                        # 오늘 등록된 횟수 카운트
                        latest_additions[pair_key] += len(today_dates)
            
            # 2. 마지막으로 등록된 데이터만 남기고 삭제
            for p in participants_in_groups:
                if p not in self.past_dates:
                    self.past_dates[p] = {}
                    continue
                
                for q in participants_in_groups:
                    if p == q:
                        continue
                    
                    if q not in self.past_dates[p]:
                        self.past_dates[p][q] = []
                        continue
                    
                    pair_key = tuple(sorted([p, q]))
                    if pair_key in latest_additions and latest_additions[pair_key] > 0:
                        # 오늘 데이터 개수 확인
                        today_count = self.past_dates[p][q].count(today_str)
                        
                        # 마지막 데이터 하나만 남기고 삭제 (최신 데이터 유지)
                        if today_count > 1:
                            # 오늘 날짜 데이터 전부 제거
                            self.past_dates[p][q] = [d for d in self.past_dates[p][q] if d != today_str]
                            
                            # 마지막 데이터 하나만 추가
                            self.past_dates[p][q].append(today_str)
                            
                            print(f"[디버깅] {p}와 {q} 쌍에서 최신 데이터 하나만 유지, {today_count-1}개 삭제됨")
        
        # 삭제 후 카운트
        today_count_after = 0
        for p in self.past_dates:
            for q in self.past_dates.get(p, {}):
                if q in self.past_dates[p]:
                    today_count_after += self.past_dates[p][q].count(today_str)
        print(f"[디버깅] 오늘 날짜 데이터 삭제 후 기록 수: {today_count_after}")
        
        # 새로운 그룹 데이터 추가
        for grp in groups:
            for i in grp:
                for j in grp:
                    if i != j:
                        if i not in self.past_dates:
                            self.past_dates[i] = {}
                        if j not in self.past_dates[i]:
                            self.past_dates[i][j] = []
                        self.past_dates[i][j].append(today_str)
        
        # 추가 후 카운트
        today_count_final = 0
        for p in self.past_dates:
            for q in self.past_dates.get(p, {}):
                if q in self.past_dates[p]:
                    today_count_final += self.past_dates[p][q].count(today_str)
        print(f"[디버깅] 새 데이터 추가 후 오늘 날짜 기록 수: {today_count_final}")
        
        self.save_past_cooccurrence()

    @staticmethod
    def _partition_group_sizes(n: int) -> List[int]:
        """Divide n participants into groups of 4 or 5."""
        r = n % 4
        num_fives = r
        num_fours = (n - 5 * r) // 4
        return [5] * num_fives + [4] * num_fours 