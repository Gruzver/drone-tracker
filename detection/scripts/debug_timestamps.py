#!/usr/bin/env python3

"""
Debug de timestamps - sincronización
"""

import rclpy
from rclpy.node import Node
from drone_tracker_msgs.msg import PersonDetectionArray, DroneState
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy


class TimestampDebugger(Node):
    def __init__(self):
        super().__init__('timestamp_debugger')
        
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        self.last_drone_timestamp = None
        self.detections_timestamps = []
        
        self.sub_detections = self.create_subscription(
            PersonDetectionArray,
            '/detection/persons',
            self.detections_callback,
            qos
        )
        
        self.sub_drone = self.create_subscription(
            DroneState,
            '/telemetry/drone/state',
            self.drone_callback,
            qos
        )
    
    def detections_callback(self, msg):
        ts_det = msg.timestamp.sec + msg.timestamp.nanosec / 1e9
        self.detections_timestamps.append(ts_det)
        
        if self.last_drone_timestamp:
            desfase = abs(ts_det - self.last_drone_timestamp)
            
            if desfase > 0.05:  # >50ms de desfase
                self.get_logger().warn(
                    f'⚠️ DESFASE GRANDE: {desfase*1000:.1f}ms\n'
                    f'   Detección: {ts_det:.6f}\n'
                    f'   Dron:      {self.last_drone_timestamp:.6f}'
                )
            else:
                self.get_logger().info(f'✅ Desfase OK: {desfase*1000:.1f}ms')
    
    def drone_callback(self, msg):
        self.last_drone_timestamp = msg.timestamp.sec + msg.timestamp.nanosec / 1e9


def main(args=None):
    rclpy.init(args=args)
    node = TimestampDebugger()
    rclpy.spin(node)


if __name__ == '__main__':
    main()