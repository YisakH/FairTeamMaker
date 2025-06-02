import random
import math
import json
from datetime import date, timedelta, datetime
from typing import List, Dict, Tuple

class TeamGenerator:
    def __init__(self, team_history_file: str = "data/team_history.json"):
        self.team_history_file = team_history_file
        self.past_dates: Dict[str, Dict[str, List[str]]] = {}

    def load_past_cooccurrence(self, participants: List[str], window_days: int = 60) -> None:
        """Load and prune past co-occurrence data from team history."""
        team_history = []
        try:
            with open(self.team_history_file, "r", encoding='utf-8') as f:
                team_history = json.load(f)
        except FileNotFoundError:
            # print(f"[디버깅] 팀 히스토리 파일이 존재하지 않음: {self.team_history_file}")
            pass # 파일이 없으면 빈 히스토리로 시작
        except json.JSONDecodeError:
            # print(f"[디버깅] 팀 히스토리 JSON 파싱 오류: {self.team_history_file}")
            pass # 파싱 오류 시 빈 히스토리로 시작

        today = date.today()
        cutoff_date = today - timedelta(days=window_days)
        # print(f"[디버깅] 날짜 범위: {cutoff_date} ~ {today}")

        self.past_dates = {p: {q: [] for q in participants if p != q} for p in participants}

        for record in team_history:
            try:
                record_date_str = record.get("date")
                if not record_date_str:
                    continue

                # ISO 문자열에서 날짜 객체로 변환 (시간대 정보는 무시)
                record_dt = datetime.fromisoformat(record_date_str.replace("Z", "+00:00"))
                record_date_obj = record_dt.date()

                if record_date_obj >= cutoff_date:
                    groups = record.get("groups", [])
                    for group in groups:
                        for i in range(len(group)):
                            for j in range(i + 1, len(group)):
                                p1, p2 = group[i], group[j]
                                if p1 in self.past_dates and p2 in self.past_dates.get(p1, {}):
                                    self.past_dates[p1][p2].append(record_date_obj.isoformat())
                                if p2 in self.past_dates and p1 in self.past_dates.get(p2, {}):
                                    self.past_dates[p2][p1].append(record_date_obj.isoformat())
            except ValueError: # datetime.fromisoformat 파싱 오류 처리
                # print(f"[디버깅] 잘못된 날짜 형식의 팀 히스토리 레코드: {record_date_str}, 오류: {e}")
                continue
            except Exception as e:
                # print(f"[디버깅] 팀 히스토리 레코드 처리 중 예외 발생: {record}, 오류: {e}")
                continue
        
        # print(f"[디버깅] 과거 동반 발생 정보 로드 완료. {len(self.past_dates)}명의 참가자에 대한 정보 처리.")

    def get_cooccurrence_info(self, participants: List[str], lam: float = 0.7) -> Dict[str, Dict[str, Dict]]:
        """Get detailed co-occurrence information for all pairs."""
        info = {}
        if not participants: # 참가자가 없으면 빈 정보 반환
            return info

        for p in participants:
            info[p] = {}
            for q in participants:
                if p == q:
                    continue
                
                # self.past_dates에 p나 q가 없을 수 있으므로 안전하게 접근
                dates = self.past_dates.get(p, {}).get(q, [])
                count = len(dates)
                last_occurrence = max(dates) if dates else None
                
                probability = math.exp(-lam * count)
                
                info[p][q] = {
                    "count": count,
                    "probability": probability,
                    "last_occurrence": last_occurrence
                }
        return info

    def _generate_groups_weighted_random(self, participants: List[str], lam: float = 3.0) -> List[List[str]]:
        """
        Original group generation method using weighted random selection.
        Keep this as a fallback for small participant counts or specific requests.
        """
        n = len(participants)
        if n == 0:
            return []
        sizes = self._partition_group_sizes(n)
        random.shuffle(sizes)

        remaining = participants.copy()
        groups: List[List[str]] = []

        for size in sizes:
            if not remaining: break # 남은 참가자가 없으면 종료

            # 리더 선택 시 remaining이 비어있을 수 있는 경우 방지
            if not remaining:
                 # print("[경고] _generate_groups_weighted_random: 리더를 선택할 남은 참가자가 없습니다.")
                 break
            leader = random.choice(remaining)
            group = [leader]
            remaining.remove(leader)

            while len(group) < size:
                if not remaining: break # 남은 참가자가 없으면 종료
                weights = []
                # cand_list는 실제 remaining에 있는 참가자들로만 구성
                cand_list = [cand for cand in remaining if cand is not None]
                if not cand_list:
                    # print("[경고] _generate_groups_weighted_random: 가중치를 계산할 후보자가 없습니다.")
                    break # 더 이상 선택할 후보가 없으면 중단

                for cand in cand_list:
                    # group의 멤버와 cand 간의 과거 만남 횟수 계산
                    cnt = 0
                    for mem in group:
                        # self.past_dates.get(mem, {}).get(cand, []) 접근 시 mem이나 cand가 없을 수 있음을 고려
                        cnt += len(self.past_dates.get(mem, {}).get(cand, []))
                    weights.append(math.exp(-lam * cnt))
                
                # weights 리스트가 비어있거나 모든 가중치가 0인 경우 방지
                if not weights or all(w == 0 for w in weights):
                    # print("[경고] _generate_groups_weighted_random: 모든 가중치가 0이거나 weights 리스트가 비어있습니다. 무작위 선택을 수행합니다.")
                    if cand_list: # 선택할 후보가 있다면 무작위 선택
                        chosen = random.choice(cand_list)
                    else: # 후보도 없으면 루프 탈출
                        break
                else:
                    chosen = random.choices(cand_list, weights=weights, k=1)[0]
                
                group.append(chosen)
                if chosen in remaining: # chosen이 remaining에 있는지 한번 더 확인 후 제거
                    remaining.remove(chosen)

            groups.append(group)

        return groups

    def _get_cooccurrence_counts(self, participants: List[str]) -> Dict[str, Dict[str, int]]:
        """
        Generate a dictionary of co-occurrence counts for all participant pairs.
        """
        counts = {}
        if not participants:
            return counts
            
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
        n = len(participants)
        if n == 0:
            return []
        sizes = self._partition_group_sizes(n)
        shuffled_participants = participants.copy() # 원본 변경 방지
        random.shuffle(shuffled_participants)
        
        groups = []
        idx = 0
        for size in sizes:
            if idx < n: # 참가자 인덱스가 범위를 벗어나지 않도록 확인
                group = shuffled_participants[idx:idx+size]
                if group: # 빈 그룹이 추가되지 않도록
                     groups.append(group)
                idx += size
            else:
                break
        return groups

    def _group_cost(self, group: List[str], counts: Dict[str, Dict[str, int]], lam: float) -> float:
        """
        Compute the cost of a group based on co-occurrence counts.
        Higher counts result in higher costs. Cost is normalized between 0 and 1 per pair.
        """
        cost = 0.0
        num_pairs = 0
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                p1, p2 = group[i], group[j]
                # counts.get(p1, {}).get(p2, 0) 으로 안전하게 접근
                count = counts.get(p1, {}).get(p2, 0) \
                # 비용 함수: (1 - exp(-lam * count)) -> count가 0이면 0, count가 크면 1에 가까워짐
                cost += (1 - math.exp(-lam * count))
                num_pairs += 1
        # 그룹 내 평균 쌍 비용 반환 (선택적, 정규화 효과)
        # return cost / num_pairs if num_pairs > 0 else 0.0
        return cost # 여기서는 총 비용을 사용

    def _total_cost(self, groups: List[List[str]], counts: Dict[str, Dict[str, int]], lam: float) -> float:
        """
        Compute the total cost for all groups.
        """
        total_c = 0.0
        for g in groups:
            if g: # 빈 그룹은 비용 계산에서 제외
                total_c += self._group_cost(g, counts, lam)
        return total_c

    def _neighbor_partition(self, groups: List[List[str]]) -> Tuple[List[List[str]], Tuple[int, int, int, int] | None]:
        """
        Generate a neighbor solution by swapping two participants in different groups.
        Returns new groups and the swap indices ((g1_idx, p1_idx_in_g1), (g2_idx, p2_idx_in_g2)).
        Returns None for swap_info if a valid swap cannot be made (e.g. less than 2 groups or groups are too small).
        """
        new_groups = [g.copy() for g in groups if g] # 빈 그룹 제거 후 복사
        if len(new_groups) < 2: # 그룹이 2개 미만이면 스왑 불가
            return new_groups, None 

        # 유효한 (멤버가 있는) 그룹들의 인덱스 찾기
        valid_group_indices = [i for i, g in enumerate(new_groups) if g]
        if len(valid_group_indices) < 2:
             return new_groups, None

        # 두 개의 다른 유효한 그룹 랜덤 선택
        g1_idx, g2_idx = random.sample(valid_group_indices, 2)
        
        group1 = new_groups[g1_idx]
        group2 = new_groups[g2_idx]

        if not group1 or not group2: # 선택된 그룹 중 하나라도 비어있으면 스왑 불가 (이론상 위에서 필터링됨)
            return new_groups, None

        p1_idx_in_g1 = random.randrange(len(group1))
        p2_idx_in_g2 = random.randrange(len(group2))
        
        # 교환
        group1[p1_idx_in_g1], group2[p2_idx_in_g2] = group2[p2_idx_in_g2], group1[p1_idx_in_g1]
        
        # 변경된 그룹을 new_groups에 다시 할당
        # new_groups[g1_idx] = group1 # 이미 new_groups의 리스트를 직접 수정했으므로 필요 없음
        # new_groups[g2_idx] = group2

        return new_groups, (g1_idx, p1_idx_in_g1, g2_idx, p2_idx_in_g2)

    def _simulated_annealing(
        self,
        participants: List[str],
        counts: Dict[str, Dict[str, int]],
        lam: float = 3.0, # lam은 비용함수에서 사용, 여기서는 기본값만 명시
        initial_temp: float = 100.0,
        cooling_rate: float = 0.995,
        temp_min: float = 0.1,
        max_iter: int = 5000
    ) -> List[List[str]]:
        """
        Optimize the partition using simulated annealing algorithm.
        """
        if not participants:
            return []

        current_partition = self._initial_partition(participants)
        # 초기 파티션이 비어있거나, 유효하지 않은 경우 (예: 참가자 한명인데 그룹 생성 불가) 처리
        if not current_partition or not any(current_partition): # 모든 그룹이 비었는지 확인
            # print("[정보] 초기 파티션 생성 실패 또는 빈 파티션. SA를 진행할 수 없습니다.")
            return current_partition # 빈 리스트 또는 생성된 그대로 반환

        best_partition = [g.copy() for g in current_partition if g] # 빈 그룹 제외하고 복사
        
        current_cost = self._total_cost(current_partition, counts, lam)
        best_cost = current_cost
        T = initial_temp
        
        for iteration in range(max_iter):
            if T < temp_min:
                break
            
            # 현재 파티션이 유효한지 (SA 진행 가능한지) 확인
            valid_groups_in_current = [g for g in current_partition if g]
            if len(valid_groups_in_current) < 2 and len(participants) > max(self._partition_group_sizes(len(participants))): # 그룹이 하나거나, 참가자가 많아 스왑이 의미있는 경우
                 # print(f"[정보] 반복 {iteration}: 스왑할 유효 그룹 부족 또는 단일 그룹. SA 중단.")
                 break # 더 이상 개선 여지 없음

            candidate_partition, swap_info = self._neighbor_partition(current_partition)
            
            if swap_info is None: # 유효한 스왑이 아니면 다음 반복으로
                T *= cooling_rate # 온도는 계속 낮춤
                continue

            candidate_cost = self._total_cost(candidate_partition, counts, lam)
            delta_cost = candidate_cost - current_cost
            
            if delta_cost < 0 or random.random() < math.exp(-delta_cost / T):
                current_partition = [g.copy() for g in candidate_partition if g] # 빈 그룹 제외
                current_cost = candidate_cost
                
                if candidate_cost < best_cost:
                    best_partition = [g.copy() for g in current_partition if g] # 빈 그룹 제외
                    best_cost = candidate_cost
            
            T *= cooling_rate
        
        return [g for g in best_partition if g] # 최종적으로 빈 그룹 제거 후 반환

    @staticmethod
    def _partition_group_sizes(n: int) -> List[int]:
        """Divide n participants into groups of 4 or 5, prioritizing 4."""
        if n <= 0:
            return []
        if n <= 5: # 5명 이하면 한 그룹
            return [n]
        if n == 6: # 6명은 3명씩 두 그룹
            return [3, 3]
        if n == 7: # 7명은 4명, 3명
            return [4, 3]
        # 8명 이상: 4명 또는 5명으로 구성, 4명 그룹을 최대한 많이 만듦
        # num_fours * 4 + num_fives * 5 = n
        # num_fives = (n - 4 * num_fours) / 5
        # n_mod_5 = n % 5  (0, 1, 2, 3, 4)
        # if n_mod_5 == 0: (num_fives = n/5, num_fours = 0) -> 5,5,...
        # if n_mod_5 == 1: (4,4,...,5) -> n = 4k+1 -> (k-1)*4 + 5. (n-5)/4 fours. (n-5) % 4 == 0.
        #    e.g. n=6 (X, 위에서 처리), n=11 (4,4,3 -> X), n=16 (4,4,4,4), n=21 (4,4,4,4,5)
        # if n_mod_5 == 2: (4,4,...,4,4,?) -> n = 4k+2. (k-2)*4 + 5+5. e.g. n=7 (X), n=12 (4,4,4), n=17(4,4,4,5)
        # if n_mod_5 == 3: (4,...,?) -> n=4k+3. (k)*4 + 3. e.g. n=3(X), n=7(X), n=13(4,4,5)
        # if n_mod_5 == 4: (4,...,?) -> n=4k. (k)*4. e.g. n=4(X), n=8(4,4), n=9(4,5)

        num_fives = 0
        num_fours = 0

        # 가능한 5인 그룹의 최대 개수부터 시작하여 4인 그룹으로 채우는 방식
        # 또는 4인 그룹의 개수를 n // 4로 시작하고 나머지를 조정
        
        # 단순화된 로직: 나머지에 따라 5인 그룹 개수 결정
        # n = 4a + 5b
        # 나머지가 0: 모두 4 (예: 8 -> 4,4; 12 -> 4,4,4) 단, 5의 배수이면 5로 (10 -> 5,5; 20 -> 5,5,5,5)
        # 나머지가 1: 5 하나 (예: 9 -> 4,5; 13 -> 4,4,5)
        # 나머지가 2: 5 둘 (예: 7 -> 3,4(X); 12 -> 4,4,4(O); 17 -> 4,4,4,5(X) -> 5,4,4,4 -> 5,5,?) -> [4,4,5,x] -> [4,4,4,5]
        # 17 = 4*x + 5*y. y=1, 4x=12, x=3. [4,4,4,5]
        # 12 = 4*x + 5*y. y=0, x=3. [4,4,4].
        # n = 7 (4,3) / n=12 (4,4,4) / n=17 (4,4,4,5)
        # 나머지가 3: 5 (X), 4 (X), 3 하나 (예: 11 -> 4,4,3; )
        # n = 3 (3) / n=8 (4,4) / n=13 (4,4,5)
        # 나머지가 4: 4 (예: 4 / 8 / 9 -> 4,5)
        
        # 반복적으로 5 또는 4를 빼면서 그룹 크기 결정 (Knapsack 유사 문제로 풀 수도 있음)
        # 여기서는 간단한 규칙 기반으로 처리
        
        # n을 4와 5의 조합으로 만드는 것을 목표로 함.
        # 3명짜리 그룹은 가급적 피함 (7명일 때 [4,3] 제외)
        # 6명일 때 [3,3]
        
        q, r = divmod(n, 4) # n = 4*q + r
        
        if r == 0: # 4의 배수 (4, 8, 12, ...)
            num_fours = q
            num_fives = 0
        elif r == 1: # 4q + 1 (5, 9, 13, ...)
            if q >= 1: # (n=5 -> 5; n=9 -> 4,5; n=13 -> 4,4,5)
                num_fours = q - 1
                num_fives = 1
            else: # n=1, 실제로는 n>=2 가정하므로 발생 안함. n=1 이면 [1]
                num_fours = 0 
                num_fives = 0 # 오류 또는 [1]과 같은 처리 필요
                if n==1: return [1] # 이 함수는 최소 2명 이상을 가정.
        elif r == 2: # 4q + 2 (2, 6, 10, 14, ...)
            if q >= 2: # (n=10 -> 5,5; n=14 -> 4,5,5)
                num_fours = q - 2
                num_fives = 2
            elif q == 1: # n=6 -> 3,3 (위에서 처리)
                 # 이 로직에서는 [3,3] 대신 [?,?] -> 현재 규칙으로는 [4,2] (X) -> [5,1] (X)
                 # 6명은 [3,3]으로 고정했으므로 이 분기로 안옴.
                 # 만약 6명 처리가 없다면, num_fours=q-2 (음수) 되므로 수정 필요.
                 # 여기서는 q>=2 가정.
                num_fours = 0 # 임시
                num_fives = 0 # 임시
            else: # n=2 -> [2]
                if n==2: return [2]
        elif r == 3: # 4q + 3 (3, 7, 11, 15, ...)
            if q >= 1: # (n=7 -> 4,3 (위에서 처리); n=11 -> 4,4,3 -> 여기서는 5,?)
                       # 11 = 4*q+3 -> q=2. num_fours = q+1-2 = 1. num_fives = 1. 4*1+5*1 = 9 (X)
                       # 11 = 4* (q-x) + 5*y.
                       # 11 -> 5,3,3(X) / 4,4,3 (O)
                       # 15 -> 5,5,5 / 4,4,4,3 (O)
                num_fours = q + 1 # (q+1)*4 = 4q+4. (n=4q+3). (4q+4) - 1. -> 5를 하나 줄이고 4를 하나 늘리는 방식?
                               # 15 -> q=3. 4*4 = 16. num_fours = 4. num_fives = -1/5 (X)
                               # 15 -> 4*a + 5*b. b=3, a=0. [5,5,5]
                               # 11 -> b=1, 4a=6 (X). b=0, 4a=11 (X).
                               # 11의 경우 4,4,3이 최적이지만, 4,5로만 구성하려면? 5,2,2,2 (X)
                               # 11 -> 4,?,?.  11-4=7. 7->4,3.   [4,4,3]
                               # 11 -> 5,?,?.  11-5=6. 6->3,3.   [5,3,3]
                # 3인 그룹을 허용하지 않는다면, 이 경우 처리가 복잡해짐.
                # 여기서는 4, 5 조합을 우선.
                # n = 4a + 3. 가장 가까운 5의 배수 또는 4의 배수로.
                # (n % 5 == 3) -> n = 5k + 3. -> k*5 + 3. [5,5,...,3]
                # (n % 4 == 3) -> n = 4k + 3. -> k*4 + 3. [4,4,...,3]
                # 만약 3인조를 허용한다면:
                if n == 3: return [3]
                if n == 7: return [4,3] # 이미 위에서 처리
                # 11명: 4,4,3
                # 15명: 5,5,5 or 4,4,4,3
                # 19명: 5,5,5,4 or 4,4,4,4,3
                # 일단 4,5 조합이 안되면 3을 포함하는 조합으로.
                num_fives = (n % 4) * -1 + 4 # if n%4 == 3, num_fives = 1
                                            # if n%4 == 2, num_fives = 2
                                            # if n%4 == 1, num_fives = 3 (너무 많음)
                                            # if n%4 == 0, num_fives = 4 (너무 많음)
                # 다른 방식: 5인 그룹 개수를 먼저 결정
                if n % 5 == 0:
                    num_fives = n // 5
                    num_fours = 0
                elif n % 5 == 1: # e.g., 6 -> 4 (+2), 11 -> 4,4,3 or 5,2,2,2 (X) or 5,3 (X) -> 11: (5*1) + 6 -> 5,3,3 or 5,2,4
                                # 11 = 5*x + 4*y. x=1, 4y=6 (X). x=0, 4y=11(X).
                                # 이 경우 3이 반드시 포함되어야 함.
                                # [4,4,3] for 11.
                    if n == 1: return [1] # Should not happen for group generation
                    if n == 6: return [3,3] # 위에서 처리.
                    # 11명 -> num_fours=2, num_threes=1
                    # 16명 -> num_fours=4
                    # For n % 5 == 1, we need to make it up with 4s. (n-5k)/4 must be int.
                    # Try num_fives from (n // 5) down to 0
                    solved = False
                    for nf5 in range(n // 5, -1, -1):
                        remaining_n = n - nf5 * 5
                        if remaining_n >=0 and remaining_n % 4 == 0:
                            num_fives = nf5
                            num_fours = remaining_n // 4
                            solved = True
                            break
                    if not solved: # 3인 그룹이 필요한 경우 (e.g. 11)
                        if n==1: return [1]
                        if n==6: return [3,3] # 예외 케이스
                        # (n % 4 == 3 이고, n % 5 != 0,1, )
                        # (n=11: 11%5=1, 11%4=3)
                        # For 11: 2*4 + 1*3
                        # For 13: 2*4 + 1*5 or 1*4 + ?
                        # Default to a configuration with 3s if 4s and 5s don't work out perfectly
                        # This part can be complex. Sticking to a simpler heuristic:
                        if n == 11: return [4,4,3]
                        if n == 13: return [4,4,5] # or 5,4,4
                        # A more general solution for n >= 8:
                        num_threes = 0
                        if n % 4 == 1 and n > 5: # 9, 13, 17
                            num_fives = 1
                            num_fours = (n - 5) // 4
                        elif n % 4 == 2 and n > 6 : # 10, 14, 18
                            num_fives = 2
                            num_fours = (n - 10) // 4
                        elif n % 4 == 3 and n > 7: # 11, 15, 19
                             # For 11: [4,4,3]. For 15: [5,5,5]. For 19: [5,5,5,4]
                            if n == 11: return [4,4,3]
                            elif n % 5 == 0 : # 15
                                num_fives = n // 5; num_fours = 0
                            elif n % 5 == 4: # 19 -> 19 = 5*3 + 4*1
                                num_fives = (n // 5) -1 # e.g. 19//5 = 3. nf5=3. n-15=4. nf4=1.
                                num_fours = (n - num_fives * 5) // 4
                                if num_fours < 0: # fallback if calculation is off
                                     num_fives = (n//5)
                                     num_fours = (n - num_fives*5)//4
                                     if n - num_fives*5 - num_fours*4 !=0: # still not good
                                        # Try to maximize 4s
                                        num_fours = n // 4
                                        rem = n % 4
                                        if rem == 0: num_fives = 0
                                        elif rem == 1: num_fives = 1; num_fours -=1
                                        elif rem == 2: num_fives = 2; num_fours -=2 # implies groups of 2 if num_fours <0
                                        elif rem == 3: num_fives=0; num_fours = (n-3)//4; num_threes=1


                        elif n % 4 == 0: # 8, 12, 16
                            num_fours = n // 4
                            num_fives = 0
                        else: # Fallback for unhandled small N or complex cases
                            # This should ideally not be reached if above cases are comprehensive for n >=8
                            # Default to as many 4s as possible, then 5s, then 3s.
                            num_fours = n // 4
                            rem = n % 4
                            if rem == 0: num_fives = 0; num_threes = 0;
                            elif rem == 1: # 1, 5, 9, 13...
                                if n == 1: return [1]
                                num_fives = 1; num_fours -= 1; num_threes = 0;
                            elif rem == 2: # 2, 6, 10, 14...
                                if n == 2: return [2]
                                num_fives = 0; num_fours -=1 ; num_threes = 2; # 4,3,3 for 10, 3,3 for 6
                                if n == 10: num_fives=2; num_fours=0; num_threes=0; # [5,5]
                                elif n == 6: return [3,3]
                            elif rem == 3: # 3, 7, 11, 15...
                                if n == 3: return [3]
                                num_threes = 1; num_fours = (n-3)//4; num_fives = 0;
                                if n == 7: return [4,3]

                        # Ensure calculated fours and fives are non-negative
                        num_fours = max(0, num_fours)
                        num_fives = max(0, num_fives)
                        num_threes = max(0, num_threes)

                        # Recalculate if sum is not n due to adjustments
                        if num_fours * 4 + num_fives * 5 + num_threes * 3 != n:
                            # Fallback: Prioritize 4s, then 5s, then 3s
                            # This is a greedy approach
                            sizes = []
                            temp_n = n
                            while temp_n >= 5:
                                if temp_n % 4 == 0 and temp_n // 4 >=1 : # Prefer 4s if it makes sense
                                    num_can_be_fours = temp_n // 4
                                    # if temp_n - num_can_be_fours*4 == 0, all fours
                                    # Check if using a 5 makes it better
                                    if temp_n - 5 >= 0 and (temp_n - 5) % 4 == 0 :
                                        sizes.append(5)
                                        temp_n -=5
                                    else:
                                        sizes.append(4)
                                        temp_n -=4
                                elif temp_n >= 5 :
                                    sizes.append(5)
                                    temp_n -= 5
                                else: # Should not happen if temp_n >= 5
                                    break
                            while temp_n >= 4:
                                sizes.append(4)
                                temp_n -= 4
                            while temp_n > 0 and temp_n <4: # Remaining 1,2,3
                                if temp_n > 0: sizes.append(temp_n)
                                temp_n = 0
                            return sizes

        sizes = [4] * num_fours + [5] * num_fives
        # If sum is not n, it implies 3s are needed or initial logic for small n was better
        current_sum = sum(sizes)
        if current_sum != n:
            # This part needs robust handling for all n.
            # The provided logic for n <= 7 and the divmod based one tries to cover cases.
            # If still not matching, it indicates a gap in the rules.
            # For simplicity, if n < 8 and not covered, it's handled by specific cases.
            # For n >= 8, the 4s and 5s combination should ideally work,
            # or include 3s explicitly.
            # Example: n=11. num_fours=2, num_threes=1 -> [4,4,3]
            # Example: n=1. sizes=[], current_sum=0. n=1.
            # Fallback for numbers like 1, 2, 3 if they reach here through complex paths
            if n > 0 and n < 4 : return [n]
            if n == 0 : return []
            # If logic above for num_fours, num_fives for n >=8 failed:
            # Default strategy for n >= 8: fill with 4s, then adjust.
            # This is a common strategy for this problem.
            num_fours_strict = n // 4
            remainder = n % 4
            final_sizes = []
            if remainder == 0: # 8, 12, 16
                final_sizes = [4] * num_fours_strict
            elif remainder == 1: # 9, 13, 17
                if num_fours_strict >= 1:
                    final_sizes = [4] * (num_fours_strict - 1) + [5]
                else: # n=1, 5 (5 handled by [n] if n<=5)
                    final_sizes = [n] if n<=5 else [4, (n-4)] # Should be [5] for n=5
                    if n==1: final_sizes=[1]
                    elif n==5: final_sizes=[5]
                    # For n=1, this function might not be the best place.
            elif remainder == 2: # 6, 10, 14, 18
                if num_fours_strict >= 2: # e.g. 10 -> 4*0 + 5*2. [5,5]
                    final_sizes = [4] * (num_fours_strict - 2) + [5,5]
                elif num_fours_strict == 1: # n=6. [3,3]
                    final_sizes = [3,3]
                else: # n=2
                    final_sizes = [n]
            elif remainder == 3: # 7, 11, 15, 19
                # n=7 -> [4,3]
                # n=11 -> [4,4,3]
                # n=15 -> [5,5,5]
                # n=19 -> [5,5,5,4]
                if n == 7: final_sizes = [4,3]
                elif n == 11: final_sizes = [4,4,3]
                elif n == 15: final_sizes = [5,5,5]
                elif n == 19: final_sizes = [4]*1 + [5]*3 # [4,5,5,5] or [5,5,5,4]
                else: # Other 4k+3
                     final_sizes = [4]*num_fours_strict + [3] if num_fours_strict > 0 else [3]


            if sum(final_sizes) == n and all(s > 0 for s in final_sizes):
                 return final_sizes
            else: # Ultimate fallback if logic is still off for some n
                 # This should be a very robust partitioner.
                 # For now, if sizes don't sum up, it's an issue.
                 # print(f"Warning: _partition_group_sizes could not partition {n} perfectly with current rules. Sum: {sum(sizes)}")
                 # Fallback to simple n // 4 and handle remainder with a group of n % 4 if non-zero
                 gs = []
                 nn = n
                 while nn > 0:
                     if nn >= 5:
                         gs.append(5)
                         nn -= 5
                     elif nn == 4:
                         gs.append(4)
                         nn -= 4
                     elif nn > 0:
                         gs.append(nn)
                         nn = 0
                 if sum(gs) == n: return gs
                 else: # Should not happen
                     return [n] if n > 0 else []


        # 최종 반환 전, 합계 확인
        if sum(sizes) != n and n > 0 :
            # print(f"[경고] _partition_group_sizes: 최종 그룹 크기 합계({sum(sizes)})가 전체 인원({n})과 불일치. 재조정 시도.")
            # 이 경우, 위에서 처리된 n<=7 또는 특정 값(11,13,15,19 등)에 대한 로직을 타지 못한 것.
            # 매우 일반적인 분할 로직 (최대한 4 또는 5로 채우기)
            res = []
            temp_n = n
            num_fives_try = temp_n // 5
            rem_after_fives = temp_n % 5

            if rem_after_fives == 0: # 5, 10, 15, 20
                res = [5] * num_fives_try
            elif rem_after_fives == 1: # 6, 11, 16, 21
                if num_fives_try >= 1: # 6 -> 5,1 (X) -> 3,3. 11 -> 5,5,1 (X) -> 4,4,3
                    if n == 6: return [3,3]
                    if n == 11: return [4,4,3]
                    res = [5] * (num_fives_try -1) + [4,2] if n== (num_fives_try-1)*5+6 else [] # not generic
                    # 16 -> 5*3 + 1 -> 5,5,5,1 (X) -> 4,4,4,4
                    # For 16: fives=3, rem=1. No. fives=2, rem=6. No. fives=1, rem=11. No. fives=0, rem=16. Yes, [4,4,4,4]
                    # Try to make remainder with 4s
                    num_4s_for_rem = 0
                    best_fives = 0
                    best_fours = 0
                    found_combo = False
                    for nf5 in range(n // 5, -1, -1):
                        rem_n = n - (nf5 * 5)
                        if rem_n >= 0 and rem_n % 4 == 0:
                            best_fives = nf5
                            best_fours = rem_n // 4
                            found_combo = True
                            break
                    if found_combo:
                        res = [5] * best_fives + [4] * best_fours
                    else: # Needs a 3 (e.g. 11, 1)
                        if n == 1 : return [1]
                        if n == 11: return [4,4,3] # Should be caught earlier
                        res = [n] # fallback
                else: # n=1
                     res = [1]
            elif rem_after_fives == 2: # 7, 12, 17, 22
                if n == 7: return [4,3]
                # 12 -> 5,5,2 (X) -> 4,4,4
                # 17 -> 5,5,5,2 (X) -> 4,4,4,5
                # Try to make remainder with 4s
                found_combo = False
                for nf5 in range(n // 5, -1, -1):
                    rem_n = n - (nf5 * 5)
                    if rem_n >= 0 and rem_n % 4 == 0:
                        best_fives = nf5
                        best_fours = rem_n // 4
                        found_combo = True
                        break
                if found_combo:
                    res = [5] * best_fives + [4] * best_fours
                else: # Needs a 3 (e.g. 7, 2)
                    if n == 2 : return [2]
                    if n == 7: return [4,3]
                    res = [n] # fallback
            elif rem_after_fives == 3: # 3, 8, 13, 18
                if n == 3: return [3]
                # 8 -> 5,3 (O) or 4,4 (O, preferred)
                # 13 -> 5,5,3 (O) or 4,4,5 (O, preferred)
                # 18 -> 5,5,5,3 (O) or 4,4,5,5 (O, preferred)
                found_combo = False
                for nf5 in range(n // 5, -1, -1):
                    rem_n = n - (nf5 * 5)
                    if rem_n >= 0 and rem_n % 4 == 0: # Prioritize 4s for remainder
                        best_fives = nf5
                        best_fours = rem_n // 4
                        found_combo = True
                        break
                if found_combo and best_fours > 0 : # if remainder can be all 4s
                     res = [5] * best_fives + [4] * best_fours
                elif n % 4 == 0 : # If n is a multiple of 4 (e.g. 8)
                    res = [4] * (n//4)
                else: # Use a 3 if needed
                    res = [5] * (n // 5) + ([3] if n % 5 == 3 else []) # Basic
                    if n == 8 : res = [4,4]
                    elif n == 13 : res = [4,4,5] # or [5,4,4]
                    elif n == 18 : res = [5,5,4,4] # sum is 18

            elif rem_after_fives == 4: # 4, 9, 14, 19
                if n == 4: return [4]
                # 9 -> 5,4 (O)
                # 14 -> 5,5,4 (O)
                # 19 -> 5,5,5,4 (O)
                res = [5] * (n // 5) + [4]
            
            if sum(res) == n and all(s > 0 for s in res):
                return res
            else:
                # Final absolute fallback, should ideally not be reached.
                # print(f"[오류] _partition_group_sizes: 최종 분할 실패 for n={n}. Defaulting to [n].")
                return [n] if n > 0 else []

        return [s for s in sizes if s > 0] # Ensure no zero-size groups are returned 