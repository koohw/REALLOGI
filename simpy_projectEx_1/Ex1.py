import simpy
def car_move(env, name, speed, shared_resource):
    position = 0
    while position < 5:
        print(f'{name} now_status position : {position}, process time : {env.now}')
        with shared_resource.request() as req:
            yield req
            print(f'{name} now_status position : {position}, process time : {env.now}')
            yield env.timeout(1)
            position += speed
            print(f'{name} now_status position : {position}, process time : {env.now}')




env = simpy.Environment()
shared_resource = simpy.Resource(env,capacity=2)

env.process(car_move(env,"AGV1",2,shared_resource))
env.process(car_move(env,"AGV2",1,shared_resource))
env.process(car_move(env,"AGV3",3,shared_resource))

env.run()
