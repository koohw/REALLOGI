import simpy

def simple_process(env):
    print(f"시작 시간: {env.now}")
    yield env.timeout(5)  # 5초 대기
    print(f"종료 시간: {env.now}")

# Simpy 환경 생성
env = simpy.Environment()
env.process(simple_process(env))  # 프로세스 등록
env.run()  # 실행
