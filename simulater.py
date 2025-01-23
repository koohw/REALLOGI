import simpy
from collections import defaultdict

# Map initialization
MAP = [
    [2, 2, 2, 2, 2, 2, 2],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [2, 2, 2, 2, 2, 2, 2]
]

# Global variables
shelf_coords = [(2, 2), (2, 4), (2, 6), (5, 2), (5, 4), (5, 6)]
exit_coords = [(0, i) for i in range(len(MAP[0])) if MAP[0][i] == 2]
stop_time = defaultdict(int)  # Stop time per coordinate
shelf_capacity = {}
agv_positions = set()  # Keeps track of current AGV positions


class AGV:
    def __init__(self, env, agv_id, start_pos, work_pos, speed=1):
        self.env = env
        self.id = agv_id
        self.start_pos = start_pos
        self.pos = start_pos
        self.work_pos = work_pos
        self.speed = speed
        self.cargo = None
        self.running = True
        self.action = env.process(self.run())

    def move(self, target):
        """Move the AGV to the target coordinate while avoiding collisions."""
        while self.pos != target:
            next_step = self.next_step(target)
            if next_step in agv_positions and next_step != target:
                yield self.env.timeout(1)  # Wait if the position is occupied
            else:
                agv_positions.discard(self.pos)
                self.pos = next_step
                agv_positions.add(self.pos)
                yield self.env.timeout(1)

    def next_step(self, target):
        """Calculate the next step towards the target."""
        x, y = self.pos
        tx, ty = target
        if x < tx:
            return (x + 1, y)
        elif x > tx:
            return (x - 1, y)
        elif y < ty:
            return (x, y + 1)
        elif y > ty:
            return (x, y - 1)
        return target

    def run(self):
        """AGV task flow."""
        global shelf_capacity

        print(f"AGV {self.id} starting at {self.pos}, heading to work position {self.work_pos}")
        yield from self.move(self.work_pos)

        while self.running:
            if shelf_capacity[self.work_pos] > 0:
                yield self.env.timeout(10)  # Work time
                shelf_capacity[self.work_pos] -= 1
                stop_time[self.work_pos] += 10
                self.cargo = 1
                print(f"AGV {self.id} picked up cargo from {self.work_pos}. Remaining: {shelf_capacity[self.work_pos]}")

                nearest_exit = self.find_nearest(exit_coords)
                yield from self.move(nearest_exit)
                yield self.env.timeout(10)  # Unloading time
                stop_time[nearest_exit] += 10
                self.cargo = None
                print(f"AGV {self.id} delivered cargo to {nearest_exit}. Returning to {self.work_pos}")

                yield from self.move(self.work_pos)
            else:
                print(f"AGV {self.id} at {self.work_pos} found no work. Checking other shelves.")
                available_shelves = [s for s in shelf_coords if shelf_capacity[s] > 0]
                if available_shelves:
                    self.work_pos = self.find_nearest(available_shelves)
                    print(f"AGV {self.id} reassigned to {self.work_pos}")
                    yield from self.move(self.work_pos)
                else:
                    print(f"AGV {self.id} found no available shelves. Stopping.")
                    self.running = False

    def find_nearest(self, targets):
        """Find the nearest target coordinate."""
        return min(targets, key=lambda t: abs(self.pos[0] - t[0]) + abs(self.pos[1] - t[1]))


def simulation(env, agv_count):
    """Initialize and run the simulation."""
    agvs = []
    start_positions = [(8, 2), (8, 3), (8, 4), (8, 5)]
    work_positions = shelf_coords[:agv_count]

    for i in range(agv_count):
        agv = AGV(env, i, start_positions[i], work_positions[i])
        agvs.append(agv)
        agv_positions.add(start_positions[i])

    while True:
        active_agvs = [agv for agv in agvs if agv.running]
        if not active_agvs and all(cap == 0 for cap in shelf_capacity.values()):
            break
        if env.now % 100 == 0:
            print(f"Time: {env.now}, Active AGVs: {len(active_agvs)}")
        yield env.timeout(1)

    print("Simulation ended. Final shelf capacities:")
    print(dict(shelf_capacity))


def main():
    try:
        agv_count = int(input("Enter the number of AGVs: ").strip())
        total_items = int(input("Enter the total number of items (multiple of 6): ").strip())

        if total_items % len(shelf_coords) != 0:
            raise ValueError("Total items must be a multiple of 6.")

        global shelf_capacity
        shelf_capacity = {coord: total_items // len(shelf_coords) for coord in shelf_coords}

        env = simpy.Environment()
        env.process(simulation(env, agv_count))
        env.run()

        print("\n=== Simulation Results ===")
        print(f"Total stop time: {sum(stop_time.values())} seconds")
        print("Remaining items per shelf:", dict(shelf_capacity))

    except ValueError as e:
        print(f"Input error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
