#coding:utf-8
#!/usr/bin/env python
import numpy as np
import sys
import random
import ConfigParser

HAVECAR = 1
WALL = 3
EMPTY = 0
CONGESTION = 2
PROBSLOW = 0.1


class Road(object):
    def __init__(self):
        # 从road.conf配置文件获取道路初始化参数
        cp = ConfigParser.SafeConfigParser()
        cp.read('road.conf')
        # 仿真时长（时间步数）
        self.simulation_times = cp.getint('road', 'simulation_times')
        # 车道数量
        self.lanes = cp.getint('road', 'lanes')
        # 车道长度（单位：元胞）
        self.length = cp.getint('road', 'road_length')
        # 初始化道路基本信息数组
        self.positionArray = np.zeros((self.lanes + 2, self.length))
        # 初始化道路换道辅助信息数组
        self.switchHelperArray = np.zeros((self.lanes + 2, self.length))
        # 初始化车速信息数组
        self.speedArray = np.zeros((self.lanes + 2, self.length))
        # 行程时间计数数组（单位：时间步）
        self.speedCounter = np.zeros((self.lanes + 2, self.length))
        # 车辆目的地信息数组
        self.desArray = np.zeros((self.lanes + 2, self.length))
        # 快速路和辅路之间屏障位置
        self.block_lane = cp.getint('road', 'block_lane')
        self.existPosition = cp.getint('road', 'exist_position')
        self.entrancePosition = cp.getint('road', 'entrance_position')
        # 初始化道路换道辅助信息数组
        '''
        switchHelperArray值-含义对应关系：
        0：栏杆
        1：快速路最左侧车道
        2-3：快速路中间N条车道
        4：快速路最右侧车道
        5：辅路左侧车道
        6：辅路右侧车道
        '''
        self.switchHelperArray[0, :] = 0
        self.switchHelperArray[1, :] = 1
        self.switchHelperArray[2, :] = 2
        self.switchHelperArray[3, :] = 3
        self.switchHelperArray[4, :] = 4
        self.switchHelperArray[5, :] = 0
        self.switchHelperArray[6, :] = 5
        self.switchHelperArray[7, :] = 6
        self.switchHelperArray[8, :] = 0
        # 初始化道路左右边界
        self.positionArray[0, :] = WALL
        self.positionArray[self.lanes + 1, :] = WALL
        self.positionArray[self.block_lane, : self.existPosition] = WALL
        self.positionArray[self.block_lane, self.existPosition + 1 : self.entrancePosition] = WALL
        self.positionArray[self.block_lane, self.entrancePosition + 1 :] = WALL
        self.speedArray[0, :] = WALL
        self.speedArray[self.lanes + 1, :] = WALL
        self.speedArray[self.block_lane, :] = WALL
        self.speedCounter[0, :] = WALL
        self.speedCounter[self.lanes + 1, :] = WALL
        self.speedCounter[self.block_lane, :] = WALL
        # 获取车辆最大速度
        self.vmax = cp.getint('road', 'vmax')
        # 获取进车概率
        self.prob_in = cp.getfloat('road', 'pro_in')
        # 获取限速开关
        self.is_limit = cp.getboolean('road', 'islimit')
        # 获取限速区速起始位置
        self.limit_begin = cp.getint('road', 'limit_begin')
        # 获取限速区结束位置
        self.limit_end = cp.getint('road', 'limit_end')
        # ？？？
        self.lane_for_st_figure = cp.getint('road', 'lane_for_st_figure')
        self.count_flow = 0
        self.travel_time = 0
        self.travel_speed = 0
        # 设置换道概率
        self.switch_lane_prob = cp.getint('road', 'switch_lane_prob')
        # 换道次数统计
        self.switch_counter = 0
        # 获取限速区限速值
        self.limit_speed = cp.getint('road', 'limit_speed')
        # 获取事故点开关
        self.iscongestion = cp.getboolean('road', 'iscongestion')
        # 获取单车道限速值
        self.vmax1 = cp.getint('road', 'vmax1')
        self.vmax2 = cp.getint('road', 'vmax2')
        self.vmax3 = cp.getint('road', 'vmax3')
        self.vmax4 = cp.getint('road', 'vmax4')
        self.vmax5 = cp.getint('road', 'vmax5')
        self.vmax6 = cp.getint('road', 'vmax6')
        self.vmax7 = cp.getint('road', 'vmax7')
        if self.iscongestion:
            # 获取事故点车道
            self.congestion_point_lane = cp.getint('road', 'congestion_point_lane')
            # 获取事故点起始位置
            self.congestion_point_point = cp.getint('road', 'congestion_point_point')
            # 获取事故点长度
            self.congestion_length = cp.getint('road', 'congestion_length')
            # 设置道路信息数组的事故点
            self.positionArray[self.congestion_point_lane,
            self.congestion_point_point: self.congestion_point_point + self.congestion_length] = CONGESTION
        # 获取停车等待时间
        self.time_can_wait = cp.getint('road', 'time_can_wait')
        self.switch_left_prob = cp.getfloat('road', 'switch_left_prob')

    def get_vmax(self, lane):
        """获取当前车道限制速度"""
        if lane == 1:
            return self.vmax1
        elif lane == 2:
            return self.vmax2
        elif lane == 3:
            return self.vmax3
        elif lane == 4:
            return self.vmax4
        elif lane == 5:
            return self.vmax5
        elif lane == 6:
            return self.vmax6
        elif lane == 7:
            return self.vmax7

    def progress(self, speed):
        """道路状态演化函数"""
        """中间变量 start"""
        """这些中间变量感觉可以尝试不放在循环里"""
        limit_speed = speed
        positionArray = self.positionArray
        speedArray = self.speedArray
        speedCounter = self.speedCounter
        desArray = self.desArray
        islimit = False
        '''中间变量 end'''
        '''中间变量：减速步使用 start'''
        gap = np.zeros(positionArray.shape)
        left_change_condition = np.zeros(positionArray.shape)
        right_change_condition = np.zeros(positionArray.shape)
        left_change_real = np.zeros(positionArray.shape)
        right_change_real = np.zeros(positionArray.shape)
        '''中间量：减速步使用 end'''
        """第一个循环：计算gap数组、执行加速步、时间步计数begin"""
        for i in range(1, positionArray.shape[0] - 1):
            gap_position_temp = sys.maxint
            """从道路最前面的一辆车开始遍历"""
            for j in range(positionArray.shape[1] - 1, -1, -1):
                '''确定当前的vmax：vmax or limit_speed start'''
                vmax = self.get_vmax(i)
                if positionArray[i, j] == 1:
                    """如果存在限速区，并且当前车辆位于限速区内，更新最大限制速度"""
                    if positionArray[i, j] == 1 and self.is_limit and self.limit_begin <= j <= self.limit_end:
                        islimit = True
                        vmax = limit_speed
                    else:
                        islimit = False
                '''确定当前的vmax：vmax or limit_speed end'''
                '''加速步骤begin'''
                speedArray[i, j] = min(speedArray[i, j] + 1, vmax)
                '''加速步骤end'''
                '''计算前车距离begin'''
                if positionArray[i, j] == 1 or positionArray[i, j] == 2:
                    """检查车辆间距是否计算正确，不正确抛出异常"""
                    if gap_position_temp - j - 1 < 0:
                        raise RuntimeError('gap error')
                    """如果是道路最前面的一辆车，gap为 sys.maxint - j - 1 """
                    gap[i, j] = gap_position_temp - j - 1
                    gap_position_temp = j
                '''计算前车距离end'''
                '''行程开始时间累计（单位：时间步）begin'''
                if self.limit_begin <= j <= self.limit_end and speedCounter[i, j] != 0:
                    speedCounter[i, j] += 1
                '''行程开始时间累计（单位：时间步）end'''
        """第一个循环：计算gap数组、执行加速步、时间步计数end"""
        '''第二个循环：逐车道换道begin'''
        for i in range(1, self.lanes + 1):
            switch_lane(positionArray, i, self.lanes, self.vmax, right_change_condition, left_change_condition,
                        speedArray, gap, left_change_real, right_change_real, self.switch_lane_prob, speedCounter, self, islimit, desArray)
        '''第二个循环：逐车道换道end'''
        '''第三个循环：换道后更新前车距离begin'''
        gap = np.zeros(positionArray.shape)
        for i in range(1, positionArray.shape[0] - 1):
            gap_position_temp = sys.maxint
            for j in range(positionArray.shape[1] - 1, -1, -1):
                if positionArray[i, j] == 1 or positionArray[i, j] == 2:
                    if gap_position_temp - j - 1 < 0:
                        raise RuntimeError('gap error')
                    gap[i, j] = gap_position_temp - j - 1
                    gap_position_temp = j
        '''第三个循环：换道后更新前车距离end'''
        '''第四个循环：减速步、随机慢化步begin'''
        for i in range(1, positionArray.shape[0] - 1):
            # 计数器，第1辆车和第2辆车减速步特殊处理：第1辆车不需要减速
            count = 1
            """记录前车距离的临时变量"""
            gap_position_temp2 = sys.maxint
            for j in range(positionArray.shape[1] - 1, -1, -1):
                '''确定当前的vmax：vmax or limit_speed'''
                vmax = limit_speed if (positionArray[i, j] == 1 and self.is_limit and self.limit_begin <= j <= self.limit_end) else self.vmax
                '''确定当前的vmax：vmax or limit_speed'''
                '''减速步begin'''
                if positionArray[i, j] == 1 or positionArray[i, j] == 2:
                    if positionArray[i, j] == 2:
                        pass
                    # 如果前方不是车辆，而是障碍物的话，不需要考虑前车速度，使用NaSch模型减速步
                    elif gap_position_temp2 < positionArray.shape[1] and positionArray[i, gap_position_temp2] == 2:
                        temp_speed = min(speedArray[i, j], gap[i, j])
                        speedArray[i, j] = max(temp_speed, 0)
                    elif count == 1:
                        pass
                    elif count == 2:
                        temp_speed = min(speedArray[i, j], gap[i, j])
                        speedArray[i, j] = max(temp_speed, 0)
                    # 如果前方是车辆的话，为了更快行进，会考虑前车速度，使用VE减速步
                    else:
                        d = max(0, gap[i, gap_position_temp2] - 1)
                        vmax_before = limit_speed if (self.is_limit and self.limit_begin <= gap_position_temp2 <= self.limit_end) else self.vmax
                        vq = min(vmax_before - 1, d)
                        vq = min(vq, speedArray[i, gap_position_temp2])
                        speedArray[i, j] = min(speedArray[i, j], gap[i, j] + vq)
                        if speedArray[i, j] > d + gap[i, j]:
                            raise RuntimeError('ve error')
                    count += 1
                    gap_position_temp2 = j
                    if speedArray[i, j] < 0:
                        raise RuntimeError('v error')
                '''减速步end'''
                '''随机慢化步begin'''
                if positionArray[i, j] == 1 and random.uniform(0, 1) <= PROBSLOW:
                    speedArray[i, j] = max(speedArray[i, j] - 1, 0)
                '''随机慢化步end'''
        '''第四个循环：减速步、随机慢化步end'''
        '''第五个循环：监测点统计数据、位置更新 begin'''
        for i in range(1, positionArray.shape[0] - 1):
            for j in range(positionArray.shape[1] - 1, -1, -1):
                '''Nasch位置更新步begin'''
                if positionArray[i, j] == 1:
                    position_next = int(j + speedArray[i, j])
                    if position_next != j:
                        '''流量&总行程时间&总行程车速统计begin'''
                        '''限速区末端为计数点'''
                        if j <= self.limit_end <= position_next:
                            self.count_flow += 1
                            self.travel_time += speedCounter[i, j]
                            self.travel_speed += (self.limit_end - self.limit_begin) / speedCounter[i, j]
                        '''流量&总行程时间&总行程车速统计end'''
                        if position_next < positionArray.shape[1]:
                            positionArray[i, position_next] = 1
                            speedArray[i, position_next] = speedArray[i, j]
                            speedCounter[i, position_next] = speedCounter[i, j]
                            desArray[i, position_next] = desArray[i, j]
                        positionArray[i, j] = 0
                        speedArray[i, j] = 0
                        speedCounter[i, j] = 0
                        desArray[i, j] = 0
                '''Nasch位置更新步end'''
        '''第五个循环：监测点统计数据、位置更新 end'''
        return positionArray


def switch_lane(positionArray, i, lanes, vmax, right_change_condition, left_change_condition, speedArray, gap, left_change_real, right_change_real, switch_lane_prob, speedCounter, road, islimit, desArray):
    for j in range(positionArray.shape[1] - 1, -1, -1):
        '''计算换道条件begin'''
        if positionArray[i, j] == 1:
            if int(road.switchHelperArray[i, j]) == 1 or int(road.switchHelperArray[i, j]) == 4:
                change = True
                tempvmax = road.get_vmax(i + 1)
                for r in range(j - tempvmax - 1, j + 1):
                    if positionArray[i + 1, r] == 1 or positionArray[i + 1, r] == 2:
                        change = False
                        break
                right_change_condition[i, j] = change
            elif road.switchHelperArray[i, j] == 3 or road.switchHelperArray[i, j] == 5:
                change = True
                tempvmax = road.get_vmax(i - 1)
                for l in range(j - tempvmax - 1, j + 1):
                    if positionArray[i - 1, l] == 1 or positionArray[i - 1, l] == 2:
                        change = False
                        break
                left_change_condition[i, j] = change
            elif road.switchHelperArray[i, j] == 2:
                change_left = True
                change_right = True
                tempvmaxl = road.get_vmax(i - 1)
                tempvmaxr = road.get_vmax(i + 1)
                for l in range(j - int(tempvmaxl) - 1, j + 1):
                    if positionArray[i - 1, l] == 1 or positionArray[i - 1, l] == 2:
                        change_left = False
                        break
                for r in range(j - int(tempvmaxr) - 1, j + 1):
                    if positionArray[i + 1, r] == 1 or positionArray[i + 1, r] == 2:
                        change_right = False
                        break
                left_change_condition[i, j] = change_left
                right_change_condition[i, j] = change_right
        '''计算换道条件end'''
        '''计算是否满足换道动机（即是否换道）begin'''
        if positionArray[i, j] == 1:
            if int(road.switchHelperArray[i, j]) == 1 or int(road.switchHelperArray[i, j]) == 4:
                if min(speedArray[i, j] + 1, vmax) > gap[i, j] and right_change_condition[
                    i, j] == 1 and random.uniform(
                        0, 1) < switch_lane_prob:
                    right_change_real[i, j] = 1
            elif int(road.switchHelperArray[i, j]) == 3 or int(road.switchHelperArray[i, j]) == 5:
                if min(speedArray[i, j] + 1, vmax) > gap[i, j] and right_change_condition[
                    i, j] == 1 and random.uniform(
                        0, 1) < switch_lane_prob:
                    right_change_real[i, j] = 1
                if min(speedArray[i, j] + 1, vmax) > gap[i, j] and left_change_condition[
                    i, j] == 1 and random.uniform(
                        0, 1) < switch_lane_prob:
                    left_change_real[i, j] = 1
            elif int(road.switchHelperArray[i, j]) == 2:
                if min(speedArray[i, j] + 1, vmax) > gap[i, j] and left_change_condition[
                    i, j] == 1 and random.uniform(
                        0, 1) < switch_lane_prob:
                    left_change_real[i, j] = 1
        '''计算是否满足换道动机（即是否换道）end'''
        '''进行换道begin'''
        if positionArray[i, j] == 1 and (left_change_real[i, j] == 1 or right_change_real[i, j] == 1):
            if int(road.switchHelperArray[i, j]) == 1 or int(road.switchHelperArray[i, j]) == 4:
                if positionArray[i + 1, j] == 1:
                    raise RuntimeError('switch error')
                positionArray[i + 1, j] = 1
                speedArray[i + 1, j] = speedArray[i, j]
                speedCounter[i + 1, j] = speedCounter[i, j]
                desArray[i + 1, j] = desArray[i, j]
            elif int(road.switchHelperArray[i, j]) == 3 or int(road.switchHelperArray[i, j]) == 5:
                if left_change_real[i, j] == 1 and right_change_real[i, j] != 1:
                    if positionArray[i - 1, j] == 1:
                        raise RuntimeError('switch error')
                    positionArray[i - 1, j] = 1
                    speedArray[i - 1, j] = speedArray[i, j]
                    speedCounter[i - 1, j] = speedCounter[i, j]
                    desArray[i - 1, j] = desArray[i, j]
                if right_change_real[i, j] == 1 and left_change_real[i, j] != 1:
                    if positionArray[i + 1, j] == 1:
                        raise RuntimeError('switch error')
                    positionArray[i + 1, j] = 1
                    speedArray[i + 1, j] = speedArray[i, j]
                    speedCounter[i + 1, j] = speedCounter[i, j]
                    desArray[i + 1, j] = desArray[i, j]
                if right_change_real[i, j] == 1 and left_change_real[i, j] == 1 and random.uniform(0, 1) < road.switch_left_prob:
                    if positionArray[i - 1, j] == 1:
                        raise RuntimeError('switch error')
                    positionArray[i - 1, j] = 1
                    speedArray[i - 1, j] = speedArray[i, j]
                    speedCounter[i - 1, j] = speedCounter[i, j]
                    desArray[i - 1, j] = desArray[i, j]
                elif right_change_real[i, j] == 1 and left_change_real[i, j] == 1:
                    if positionArray[i + 1, j] == 1:
                        raise RuntimeError('switch error')
                    positionArray[i + 1, j] = 1
                    speedArray[i + 1, j] = speedArray[i, j]
                    speedCounter[i + 1, j] = speedCounter[i, j]
                    desArray[i + 1, j] = desArray[i, j]
            elif int(road.switchHelperArray[i, j]) == 2:
                if positionArray[i - 1, j] == 1:
                    raise RuntimeError('switch error')
                positionArray[i - 1, j] = 1
                speedArray[i - 1, j] = speedArray[i, j]
                speedCounter[i - 1, j] = speedCounter[i, j]
                desArray[i - 1, j] = desArray[i, j]
            positionArray[i, j] = 0
            speedArray[i, j] = 0
            speedCounter[i, j] = 0
            desArray[i, j] = 0
            road.switch_counter += 1
        '''进行换道end'''


class CommonFollowRule(object):
    """跟驰模型"""

    def do_all_steps(self):


    @staticmethod
    def accelerate_step(i, position_array, road, gap, speed_array, speed_counter, limit_speed):
        """计算gap数组、执行加速步、时间步计数"""
        gap_position_temp = sys.maxint
        """从道路最前面的一辆车开始遍历"""
        for j in range(position_array.shape[1] - 1, -1, -1):
            '''确定当前的vmax：vmax or limit_speed start'''
            vmax = road.get_vmax(i)
            if position_array[i, j] == 1:
                """如果存在限速区，并且当前车辆位于限速区内，更新最大限制速度"""
                if position_array[i, j] == 1 and road.is_limit and road.limit_begin <= j <= road.limit_end:
                    is_limit = True
                    vmax = limit_speed
                else:
                    is_limit = False
            '''确定当前的vmax：vmax or limit_speed end'''
            '''加速步骤begin'''
            speed_array[i, j] = min(speed_array[i, j] + 1, vmax)
            '''加速步骤end'''
            '''计算前车距离begin'''
            if position_array[i, j] == 1 or position_array[i, j] == 2:
                """检查车辆间距是否计算正确，不正确抛出异常"""
                if gap_position_temp - j - 1 < 0:
                    raise RuntimeError('gap error')
                """如果是道路最前面的一辆车，gap为 sys.maxint - j - 1 """
                gap[i, j] = gap_position_temp - j - 1
                gap_position_temp = j
            '''计算前车距离end'''
            '''行程开始时间累计（单位：时间步）begin'''
            if road.limit_begin <= j <= road.limit_end and speed_counter[i, j] != 0:
                speed_counter[i, j] += 1
            '''行程开始时间累计（单位：时间步）end'''

    @staticmethod
    def compute_gap(i, position_array, gap):
        gap_position_temp = sys.maxint
        for j in range(position_array.shape[1] - 1, -1, -1):
            if position_array[i, j] == 1 or position_array[i, j] == 2:
                if gap_position_temp - j - 1 < 0:
                    raise RuntimeError('gap error')
                gap[i, j] = gap_position_temp - j - 1
                gap_position_temp = j

    @staticmethod
    def slow_down_step(i, position_array, speed_array, gap, road, limit_speed):
        # 计数器，第1辆车和第2辆车减速步特殊处理：第1辆车不需要减速
        count = 1
        """记录前车距离的临时变量"""
        gap_position_temp2 = sys.maxint
        for j in range(position_array.shape[1] - 1, -1, -1):
            '''确定当前的vmax：vmax or limit_speed'''
            vmax = limit_speed if (position_array[
                                       i, j] == 1 and road.is_limit and road.limit_begin <= j <= road.limit_end) else road.vmax
            '''确定当前的vmax：vmax or limit_speed'''
            '''减速步begin'''
            if position_array[i, j] == 1 or position_array[i, j] == 2:
                if position_array[i, j] == 2:
                    pass
                # 如果前方不是车辆，而是障碍物的话，不需要考虑前车速度，使用NaSch模型减速步
                elif gap_position_temp2 < position_array.shape[1] and position_array[i, gap_position_temp2] == 2:
                    temp_speed = min(speed_array[i, j], gap[i, j])
                    speed_array[i, j] = max(temp_speed, 0)
                elif count == 1:
                    pass
                elif count == 2:
                    temp_speed = min(speed_array[i, j], gap[i, j])
                    speed_array[i, j] = max(temp_speed, 0)
                # 如果前方是车辆的话，为了更快行进，会考虑前车速度，使用VE减速步
                else:
                    d = max(0, gap[i, gap_position_temp2] - 1)
                    vmax_before = limit_speed if (
                                road.is_limit and road.limit_begin <= gap_position_temp2 <= road.limit_end) else road.vmax
                    vq = min(vmax_before - 1, d)
                    vq = min(vq, speed_array[i, gap_position_temp2])
                    speed_array[i, j] = min(speed_array[i, j], gap[i, j] + vq)
                    if speed_array[i, j] > d + gap[i, j]:
                        raise RuntimeError('ve error')
                count += 1
                gap_position_temp2 = j
                if speed_array[i, j] < 0:
                    raise RuntimeError('v error')
            '''减速步end'''
            '''随机慢化步begin'''
            if position_array[i, j] == 1 and random.uniform(0, 1) <= PROBSLOW:
                speed_array[i, j] = max(speed_array[i, j] - 1, 0)
            '''随机慢化步end'''

    @staticmethod
    def update_position(i, position_array, speed_array, road, speed_counter, des_rray):
        for j in range(position_array.shape[1] - 1, -1, -1):
            '''Nasch位置更新步begin'''
            if position_array[i, j] == 1:
                position_next = int(j + speed_array[i, j])
                if position_next != j:
                    '''流量&总行程时间&总行程车速统计begin'''
                    '''限速区末端为计数点'''
                    if j <= road.limit_end <= position_next:
                        road.count_flow += 1
                        road.travel_time += speed_counter[i, j]
                        road.travel_speed += (road.limit_end - road.limit_begin) / speed_counter[i, j]
                    '''流量&总行程时间&总行程车速统计end'''
                    if position_next < position_array.shape[1]:
                        position_array[i, position_next] = 1
                        speed_array[i, position_next] = speed_array[i, j]
                        speed_counter[i, position_next] = speed_counter[i, j]
                        des_rray[i, position_next] = des_rray[i, j]
                    position_array[i, j] = 0
                    speed_array[i, j] = 0
                    speed_counter[i, j] = 0
                    des_rray[i, j] = 0
            '''Nasch位置更新步end'''


class CommonSwitchRule(object):
    """无倾向换道规则"""

    @staticmethod
    def switch_condition(i, j, position_array, road, right_change_condition, left_change_condition):
        if position_array[i, j] == 1:
            if int(road.switchHelperArray[i, j]) == 1 or int(road.switchHelperArray[i, j]) == 4:
                change = True
                temp_v_max = road.get_vmax(i + 1)
                for r in range(j - temp_v_max - 1, j + 1):
                    if position_array[i + 1, r] == 1 or position_array[i + 1, r] == 2:
                        change = False
                        break
                right_change_condition[i, j] = change
            elif road.switchHelperArray[i, j] == 3 or road.switchHelperArray[i, j] == 5:
                change = True
                temp_v_max = road.get_vmax(i - 1)
                for l in range(j - temp_v_max - 1, j + 1):
                    if position_array[i - 1, l] == 1 or position_array[i - 1, l] == 2:
                        change = False
                        break
                left_change_condition[i, j] = change
            elif road.switchHelperArray[i, j] == 2:
                change_left = True
                change_right = True
                temp_v_max_l = road.get_vmax(i - 1)
                temp_v_max_r = road.get_vmax(i + 1)
                for l in range(j - int(temp_v_max_l) - 1, j + 1):
                    if position_array[i - 1, l] == 1 or position_array[i - 1, l] == 2:
                        change_left = False
                        break
                for r in range(j - int(temp_v_max_r) - 1, j + 1):
                    if position_array[i + 1, r] == 1 or position_array[i + 1, r] == 2:
                        change_right = False
                        break
                left_change_condition[i, j] = change_left
                right_change_condition[i, j] = change_right

    @staticmethod
    def switch_purpose(i, j, position_array, road, speed_array, gap, right_change_real, right_change_condition,
                       left_change_condition, left_change_real, v_max, switch_lane_prob):
        if position_array[i, j] == 1:
            if int(road.switchHelperArray[i, j]) == 1 or int(road.switchHelperArray[i, j]) == 4:
                if min(speed_array[i, j] + 1, v_max) > gap[i, j] and right_change_condition[
                    i, j] == 1 and random.uniform(
                        0, 1) < switch_lane_prob:
                    right_change_real[i, j] = 1
            elif int(road.switchHelperArray[i, j]) == 3 or int(road.switchHelperArray[i, j]) == 5:
                if min(speed_array[i, j] + 1, v_max) > gap[i, j] and right_change_condition[
                    i, j] == 1 and random.uniform(
                        0, 1) < switch_lane_prob:
                    right_change_real[i, j] = 1
                if min(speed_array[i, j] + 1, v_max) > gap[i, j] and left_change_condition[
                    i, j] == 1 and random.uniform(
                        0, 1) < switch_lane_prob:
                    left_change_real[i, j] = 1
            elif int(road.switchHelperArray[i, j]) == 2:
                if min(speed_array[i, j] + 1, v_max) > gap[i, j] and left_change_condition[
                    i, j] == 1 and random.uniform(
                        0, 1) < switch_lane_prob:
                    left_change_real[i, j] = 1

    @staticmethod
    def switch(i, j, position_array, speed_array, speed_counter, des_array, road, left_change_real,
               right_change_real):
        if position_array[i, j] == 1 and (left_change_real[i, j] == 1 or right_change_real[i, j] == 1):
            if int(road.switchHelperArray[i, j]) == 1 or int(road.switchHelperArray[i, j]) == 4:
                if position_array[i + 1, j] == 1:
                    raise RuntimeError('switch error')
                position_array[i + 1, j] = 1
                speed_array[i + 1, j] = speed_array[i, j]
                speed_counter[i + 1, j] = speed_counter[i, j]
                des_array[i + 1, j] = des_array[i, j]
            elif int(road.switchHelperArray[i, j]) == 3 or int(road.switchHelperArray[i, j]) == 5:
                if left_change_real[i, j] == 1 and right_change_real[i, j] != 1:
                    if position_array[i - 1, j] == 1:
                        raise RuntimeError('switch error')
                    position_array[i - 1, j] = 1
                    speed_array[i - 1, j] = speed_array[i, j]
                    speed_counter[i - 1, j] = speed_counter[i, j]
                    des_array[i - 1, j] = des_array[i, j]
                if right_change_real[i, j] == 1 and left_change_real[i, j] != 1:
                    if position_array[i + 1, j] == 1:
                        raise RuntimeError('switch error')
                    position_array[i + 1, j] = 1
                    speed_array[i + 1, j] = speed_array[i, j]
                    speed_counter[i + 1, j] = speed_counter[i, j]
                    des_array[i + 1, j] = des_array[i, j]
                if right_change_real[i, j] == 1 and left_change_real[i, j] == 1 and random.uniform(0, 1) < road.switch_left_prob:
                    if position_array[i - 1, j] == 1:
                        raise RuntimeError('switch error')
                    position_array[i - 1, j] = 1
                    speed_array[i - 1, j] = speed_array[i, j]
                    speed_counter[i - 1, j] = speed_counter[i, j]
                    des_array[i - 1, j] = des_array[i, j]
                elif right_change_real[i, j] == 1 and left_change_real[i, j] == 1:
                    if position_array[i + 1, j] == 1:
                        raise RuntimeError('switch error')
                    position_array[i + 1, j] = 1
                    speed_array[i + 1, j] = speed_array[i, j]
                    speed_counter[i + 1, j] = speed_counter[i, j]
                    des_array[i + 1, j] = des_array[i, j]
            elif int(road.switchHelperArray[i, j]) == 2:
                if position_array[i - 1, j] == 1:
                    raise RuntimeError('switch error')
                position_array[i - 1, j] = 1
                speed_array[i - 1, j] = speed_array[i, j]
                speed_counter[i - 1, j] = speed_counter[i, j]
                des_array[i - 1, j] = des_array[i, j]
            position_array[i, j] = 0
            speed_array[i, j] = 0
            speed_counter[i, j] = 0
            des_array[i, j] = 0
            road.switch_counter += 1


class ExistSwitchRule(CommonSwitchRule):
    """快速路出口上游（不能直接驶出快速路的距离），快速路内车辆换道规则"""

    @staticmethod
    def switch_purpose(i, j, position_array, road, speed_array, gap, right_change_real, right_change_condition,
                       left_change_condition, left_change_real, v_max, switch_lane_prob, des_array):
        if position_array[i, j] == 1:
            if int(des_array[i, j]) == 1:
                '''快速路直行车辆'''
                if int(road.switchHelperArray[i, j]) == 1 \
                        and right_change_condition[i, j] == 1 \
                        and (min(speed_array[i, j] + 1, v_max) > gap[i, j]) \
                        and random.uniform(0, 1) < switch_lane_prob:
                    right_change_real[i, j] = 1
                elif int(road.switchHelperArray[i, j]) == 2 \
                        and (min(speed_array[i, j] + 1, v_max) > gap[i, j]) \
                        and random.uniform(0, 1) < switch_lane_prob:
                    if right_change_condition[i, j] == 1 and left_change_condition[i, j] == 1:
                        if random.uniform(0, 1) < 0.5:
                            right_change_real[i, j] = 1
                        else:
                            left_change_real[i, j] = 1
                    elif right_change_condition[i, j] == 1:
                        right_change_real[i, j] = 1
                    elif left_change_condition[i, j] == 1:
                        left_change_real[i, j] = 1
                elif int(road.switchHelperArray[i, j]) == 3 \
                        and left_change_condition[i, j] == 1 \
                        and min(speed_array[i, j] + 1, v_max) > gap[i, j] \
                        and random.uniform(0, 1) < switch_lane_prob:
                    left_change_real[i, j] = 1
                elif int(road.switchHelperArray[i, j]) == 4 and left_change_condition[i, j] == 1:
                    left_change_real[i, j] = 1
            elif int(des_array[i, j]) == 2:
                '''快速路准备驶出车辆'''
                if int(road.switchHelperArray[i, j]) == 1 and right_change_condition[i, j] == 1:
                    right_change_real[i, j] = 1
                elif int(road.switchHelperArray[i, j]) == 2 and right_change_condition[i, j] == 1:
                    right_change_real[i, j] = 1
                elif int(road.switchHelperArray[i, j]) == 3 and right_change_condition[i, j] == 1:
                    right_change_real[i, j] = 1
                elif int(road.switchHelperArray[i, j]) == 4:
                    pass


class FastToSide(CommonSwitchRule):
    """快速路可直接换道至辅路处换道规则"""
    pass

