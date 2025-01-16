# import simpy


# class Car:
#     def __init__(self, env, name, station, 주행시간, 충전시간):
#         """
#         SimPy 환경(env)과 차량 이름(name), 충전소(station) 리소스, 주행시간, 충전시간을 받아
#         시뮬레이션 프로세스를 env.process로 등록합니다.
#         """
#         self.env = env
#         self.name = name
#         self.station = station
#         self.주행시간 = 주행시간
#         self.충전시간 = 충전시간
        
#         # 차량이 생성됨과 동시에 run() 제너레이터 함수를 프로세스로 등록
#         env.process(self.run())

#     def run(self):
#         # 1) 먼저 주행시간만큼 시뮬레이션 시간을 진행(대기)합니다.
#         yield self.env.timeout(self.주행시간)
#         print(f'{self.name} {self.env.now}분에 도착')
        
#         # 2) 충전소 리소스를 요청
#         with self.station.request() as req:
#             yield req  # 자원이 빌 때까지 대기
#             print(f'{self.name} {self.env.now}분에 충전 시작')
            
#             # 3) 충전시간만큼 대기
#             yield self.env.timeout(self.충전시간)
#             print(f'{self.name} {self.env.now}분에 충전 완료')


# def main():
#     # 1) 시뮬레이션 환경 생성
#     env = simpy.Environment()

#     # 2) 충전소 자원(Resource) 생성
#     #    capacity=2 라면, 최대 2대의 차량이 동시에 충전 가능
#     station = simpy.Resource(env, capacity=2)

#     # 3) 여러 대의 차량을 생성하여 시뮬레이션에 등록
#     Car(env, 'Car A', station, 주행시간=3, 충전시간=2)
#     Car(env, 'Car B', station, 주행시간=1, 충전시간=4)
#     Car(env, 'Car C', station, 주행시간=2, 충전시간=1)
#     Car(env, 'Car D', station, 주행시간=5, 충전시간=3)

#     # 4) 시뮬레이션을 20분까지(또는 충분한 시간만큼) 실행
#     env.run(until=20)


# if __name__ == '__main__':
#     main()

# import simpy
# import random

# def patient(env, name, doctor, wait_times):
#     """환자 프로세스: 환자가 도착하고 대기 후 진료를 받습니다."""
#     arrival_time = env.now  # 환자가 응급실에 도착한 시간
#     print(f"{name}이(가) {arrival_time:.1f}분에 응급실에 도착했습니다.")

#     with doctor.request() as req:  # 의사 자원을 요청
#         yield req  # 대기
#         wait_time = env.now - arrival_time  # 대기 시간 계산
#         wait_times.append(wait_time)
#         print(f"{name}이(가) {env.now:.1f}분에 진료를 시작합니다 (대기 시간: {wait_time:.1f}분).")

#         consultation_time = random.randint(3, 10)  # 진료 시간은 3~10분 사이 랜덤
#         yield env.timeout(consultation_time)  # 진료 시간 동안 대기
#         print(f"{name}이(가) {env.now:.1f}분에 진료를 마쳤습니다.")

# def patient_generator(env, doctor, wait_times):
#     """환자를 일정 간격으로 생성합니다."""
#     patient_id = 0
#     while True:
#         yield env.timeout(random.expovariate(1/5))  # 평균 5분 간격으로 환자 도착
#         patient_id += 1
#         env.process(patient(env, f"환자 {patient_id}", doctor, wait_times))

# def main():
#     random.seed(42)  # 랜덤 시드 고정 (결과 재현 가능)

#     # 환경과 자원 생성
#     env = simpy.Environment()
#     doctor = simpy.Resource(env, capacity=1)  # 의사 한 명

#     # 대기 시간 저장 리스트
#     wait_times = []

#     # 환자 생성 프로세스 시작
#     env.process(patient_generator(env, doctor, wait_times))

#     # 시뮬레이션 실행 (30분)
#     env.run(until=30)

#     # 결과 출력
#     print("\n시뮬레이션 결과")
#     print(f"처리된 환자 수: {len(wait_times)}명")
#     if wait_times:
#         avg_wait_time = sum(wait_times) / len(wait_times)
#         print(f"평균 대기 시간: {avg_wait_time:.2f}분")
#     else:
#         print("진료받은 환자가 없습니다.")

# if __name__ == "__main__":
#     main()


'''import simpy

def clock(env):
    while True:
        print(f'{env.now}초 : Tick')
        yield env.timeout(1) # 1초 대기
        print(f'{env.now}초: Tack')
        yield env.timeout(1)

def main():
    env = simpy.Environment() # 환경 생성
    env.process(clock(env)) # clock 프로세스 생성
    env.run(until=10) # 10초간 실행

if __name__ == "__main__": # 만약 이름이 main이라는거면 실행
    main()'''


'''import simpy

def time(env):
    while True:
        print(f'time : {env.now} seconds')
        yield env.timeout(2)

def main():
    env = simpy.Environment()
    env.process(time(env))
    env.run(until=10)

if __name__ == "__main__":
    main()'''

'''import simpy

def talk(env):
    while True:
        print(f'A: "안녕하세요!"')
        yield env.timeout(1)
        print(f'B: "네, 안녕하세요!"')
        yield env.timeout(1)

def main():
    env = simpy.Environment()
    env.process(talk(env))
    env.run(until=6)

if __name__ == "__main__":
    main()'''

'''import simpy
import random

def bus(env, name):
    while True:
        print(f'{name}이(가) {env.now}초에 도착했습니다.')
        passengers = random.randint(1, 3)
        print(f'{name}이(가) {passengers}명의 승객을 태웠습니다.')
        yield env.timeout(5)

def main():
    env = simpy.Environment()
    env.process(bus(env, "버스 1"))
    env.run(until=20)

if __name__=="__main__":
    main()'''

'''import simpy

def water(env):
    water_count = 0 # 물을 마신 횟수
    while True:
        print(f'{env.now}초: 물을 마심')
        yield env.timeout(1) # 물을 마시는데 1초 소요
        water_count += 1
        print(f'{env.now}초: 물 다마심 (총 {water_count}잔)')
        yield env.timeout(2)

        if env.now >= 10:
            print(f'시뮬레이션 종료: 총 {water_count}잔의 물을 마심')
            break

def main():
    env = simpy.Environment()
    env.process(water(env))
    env.run(until=10)

if __name__ == "__main__":
    main()'''

'''import simpy
import random

def car(env, name, gas_station, wait_times):
    """차량이 주유소에 도착하여 주유하는 프로세스"""
    arrival_time = env.now  # 차량 도착 시간
    print(f"{name}이(가) {arrival_time:.1f}분에 주유소에 도착했습니다.")

    with gas_station.request() as req:  # 주유기 요청
        yield req  # 대기
        wait_time = env.now - arrival_time  # 대기 시간 계산
        wait_times.append(wait_time)
        print(f"{name}이(가) {env.now:.1f}분에 주유를 시작합니다 (대기 시간: {wait_time:.1f}분).")

        fueling_time = random.randint(2, 5)  # 주유 시간 2~5분 랜덤
        yield env.timeout(fueling_time)
        print(f"{name}이(가) {env.now:.1f}분에 주유를 완료했습니다.")

def car_generator(env, gas_station, wait_times):
    """차량을 평균 3분 간격으로 생성하는 프로세스"""
    car_id = 0
    while True:
        yield env.timeout(random.expovariate(1/3))  # 평균 3분 간격으로 차량 도착
        car_id += 1
        env.process(car(env, f"차량 {car_id}", gas_station, wait_times))

def main():
    random.seed(42)  # 랜덤 시드 고정

    # 환경과 자원 생성
    env = simpy.Environment()
    gas_station = simpy.Resource(env, capacity=2)  # 주유기 2대

    # 대기 시간 저장 리스트
    wait_times = []

    # 차량 생성 프로세스 시작
    env.process(car_generator(env, gas_station, wait_times))

    # 시뮬레이션 실행 (20분)
    env.run(until=20)

    # 결과 출력
    print("\n시뮬레이션 결과")
    print(f"총 주유 완료 차량 수: {len(wait_times)}대")
    if wait_times:
        max_wait_time = max(wait_times)
        avg_wait_time = sum(wait_times) / len(wait_times)
        print(f"평균 대기 시간: {avg_wait_time:.2f}분")
        print(f"가장 긴 대기 시간: {max_wait_time:.2f}분")
    else:
        print("대기 시간이 기록된 차량이 없습니다.")

if __name__ == "__main__":
    main()'''

import simpy
import random

def customer(env, name, teller, wait_times):
    arrival_time = env.now   # 고객 도착시간에 현재 할당
    print(f'{name} - {arrival_time:.1f}분에 도착')

    with teller.request() as req:
        yield req
        wait_time = env.now - arrival_time
        wait_times.append(wait_time)

        print(f'{name} - {env.now:.1f}분부터 업무 시작 (대기 시간 : {wait_time:.1f}분)')

        service_time = random.randint(2, 4)
        yield env.timeout(service_time)

        print(f'{name} - {env.now:.1f}분에 업무 완료')

def customer_generator(env, teller, wait_times):
    customer_id = 0
    while True:
        yield env.timeout(random.expovariate(1/5))
        customer_id += 1
        env.process(customer(env, f'고객 {customer_id}', teller, wait_times))

def main():
    random.seed(42)

    env = simpy.Environment()
    teller = simpy.Resource(env, capacity=1) # 은행 창구 생성, capacity=1 -> 동시에 한 명만 처기 가능능
    wait_times = []
    env.process(customer_generator(env, teller, wait_times))
    env.run(until=30) # 30분까지 진행

    print("결과")
    print(f'총 업무 완료 고객 수 : {len(wait_times)}명')
    if wait_times:
        avg_wait = sum(wait_times)/len(wait_times)
        max_wait = max(wait_times)
        print(f'평균 대기 시간 : {avg_wait:.2f}분')
        print(f'최대 대기 시간 : {max_wait:.2f}분')
    else:
        print('업무를 마친 고객이 없습니다')

if __name__ == '__main__':
    main()