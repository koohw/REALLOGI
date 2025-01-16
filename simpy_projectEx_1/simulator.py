import simpy


class AGV:
    def __init__(self, env, id, start_position, grid_map, simulator):
        """
        AGV 초기화
        :param env: Simpy 환경
        :param id: AGV의 ID
        :param start_position: 초기 위치 (x, y)
        :param grid_map: 격자 지도
        :param simulator: 시뮬레이터 객체 (통신 및 제어용)
        """
        self.env = env
        self.id = id
        self.start_position = start_position
        self.position = start_position
        self.grid_map = grid_map
        self.simulator = simulator
        self.status = "Idle"
        self.process = env.process(self.run())

    def move_to(self, target_position):
        """AGV를 목표 위치로 이동"""
        if self.status in ["Stopped", "Returning"]:
            print(f"[{self.env.now}] AGV-{self.id}: 현재 정지 또는 복귀 상태로 이동 불가")
            return
        self.position = target_position
        self.status = "Moving"

    def stop(self):
        """AGV를 정지"""
        self.status = "Stopped"
        print(f"[{self.env.now}] AGV-{self.id}: 정지")

    def resume(self):
        """AGV를 재가동"""
        if self.status == "Stopped":
            self.status = "Idle"
            print(f"[{self.env.now}] AGV-{self.id}: 재가동")

    def return_to_base(self):
        """AGV를 초기 위치로 복귀"""
        if self.status != "Stopped":
            print(f"[{self.env.now}] AGV-{self.id}: 복귀 명령은 정지 상태에서만 가능")
            return
        self.status = "Returning"
        self.position = self.start_position
        print(f"[{self.env.now}] AGV-{self.id}: 초기 위치로 복귀 완료 ({self.position})")
        self.status = "Idle"

    def run(self):
        """AGV의 동작"""
        while True:
            if self.status == "Idle":
                yield self.env.timeout(1)  # 유휴 상태 대기
            elif self.status == "Moving":
                yield self.env.timeout(1)  # 이동 중 대기
            elif self.status == "Stopped":
                yield self.env.timeout(1)  # 정지 상태 대기
            elif self.status == "Returning":
                yield self.env.timeout(1)  # 복귀 상태 대기
            yield self.env.timeout(1)


class Simulator:
    def __init__(self, env):
        """시뮬레이터 초기화"""
        self.env = env
        self.agvs = []

    def add_agv(self, agv):
        """AGV를 시뮬레이터에 추가"""
        self.agvs.append(agv)

    def send_command(self, agv_id, command):
        """AGV에 명령을 전달"""
        for agv in self.agvs:
            if agv.id == agv_id:
                if command == "Stop":
                    agv.stop()
                elif command == "Resume":
                    agv.resume()
                elif command == "Return":
                    agv.return_to_base()
                else:
                    print(f"[{self.env.now}] 시뮬레이터: 알 수 없는 명령 - {command}")


# 테스트
if __name__ == "__main__":
    # Simpy 환경 생성
    env = simpy.Environment()

    # 시뮬레이터 생성
    simulator = Simulator(env)

    # AGV 생성
    agv1 = AGV(env, id=1, start_position=(0, 0), grid_map=None, simulator=simulator)
    simulator.add_agv(agv1)

    # AGV 제어 테스트
    def control_simulation(env, simulator):
        yield env.timeout(2)
        simulator.send_command(1, "Stop")  # AGV 정지
        yield env.timeout(3)
        simulator.send_command(1, "Resume")  # AGV 재가동
        yield env.timeout(2)
        simulator.send_command(1, "Stop")  # AGV 정지
        yield env.timeout(2)
        simulator.send_command(1, "Return")  # AGV 복귀

    # Simpy 프로세스 등록
    env.process(control_simulation(env, simulator))

    # 시뮬레이션 실행
    env.run(until=15)
