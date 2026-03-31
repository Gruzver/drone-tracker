#!/usr/bin/env python3

"""
video_publisher.py

Nodo ROS2 que lee un video termico DJI y su archivo SRT de telemetria, y
publica sincronizadamente:
  - /camera/thermal/image_raw        (sensor_msgs/Image)
  - /camera/thermal/image_compressed (sensor_msgs/CompressedImage, JPEG)
  - /telemetry/drone/state           (drone_tracker_msgs/DroneState)

El ritmo de publicacion se controla mediante el parametro 'publish_rate'.
Cuando el video termina, el timer se cancela automaticamente.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import cv2
from pathlib import Path

from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge
from drone_tracker_msgs.msg import DroneState

from drone_tracker_utils import SRTParser


class VideoPublisherNode(Node):
    """
    Publica frames de video termico e telemetria SRT como topicos ROS2.

    Parametros ROS2:
        video_path      (str)  Ruta al archivo MP4 termico.
        srt_path        (str)  Ruta al archivo SRT de telemetria DJI.
        publish_rate    (int)  Frecuencia de publicacion en Hz (default: 30).
        use_compression (bool) Publicar tambien imagen JPEG comprimida (default: True).
    """

    # Identificador del sistema de coordenadas de la camara termica
    CAMERA_FRAME_ID = 'camera_thermal_optical'

    def __init__(self):
        super().__init__('video_publisher_node')

        # Parametros configurables desde la linea de comandos o launch file
        self.declare_parameter(
            'video_path',
            '/home/gr/Documents/drone-detection-project/data/raw/'
            'thermal_videos/DJI_20260210161918_0002_T.MP4',
        )
        self.declare_parameter(
            'srt_path',
            '/home/gr/Documents/drone-detection-project/data/raw/'
            'thermal_videos/DJI_20260210161918_0002_T.SRT',
        )
        self.declare_parameter('publish_rate', 30)
        self.declare_parameter('use_compression', True)

        self.video_path = self.get_parameter('video_path').value
        self.srt_path = self.get_parameter('srt_path').value
        self.publish_rate = self.get_parameter('publish_rate').value
        self.use_compression = self.get_parameter('use_compression').value

        self.get_logger().info(f'Video: {self.video_path}')
        self.get_logger().info(f'SRT:   {self.srt_path}')

        # QoS: best-effort con buffer minimo para minimizar latencia
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        # Publishers
        self.pub_image_raw = self.create_publisher(
            Image, '/camera/thermal/image_raw', qos
        )
        self.pub_image_compressed = self.create_publisher(
            CompressedImage, '/camera/thermal/image_compressed', qos
        )
        self.pub_drone_state = self.create_publisher(
            DroneState, '/telemetry/drone/state', qos
        )

        self.bridge = CvBridge()

        # Parsear SRT antes de abrir el video para fallar rapido si no existe
        try:
            self.srt_parser = SRTParser(self.srt_path)
            self.srt_parser.parse()
            self.get_logger().info(f'Parseados {len(self.srt_parser.frames)} frames del SRT.')
        except Exception as e:
            self.get_logger().error(f'Error parseando SRT: {e}')
            raise

        # Abrir captura de video
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f'No se pudo abrir el video: {self.video_path}')

        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.get_logger().info(f'Video: {width}x{height} @ {fps:.2f} FPS ({self.total_frames} frames total)')

        self.frame_count = 0

        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self._timer_callback)

        self.get_logger().info(f'Video Publisher listo. Publicando a {self.publish_rate} Hz.')

    def _timer_callback(self) -> None:
        """
        Callback del timer: lee un frame del video, obtiene la telemetria SRT
        correspondiente y publica imagen raw, imagen comprimida y DroneState.

        Cuando el video llega al final, cancela el timer.
        """
        ret, frame = self.cap.read()

        if not ret:
            self.get_logger().info('Fin del video. Deteniendo publicacion.')
            self.timer.cancel()
            return

        self.frame_count += 1

        drone_frame = self.srt_parser.get_frame(self.frame_count)
        if drone_frame is None:
            self.get_logger().warning(f'Frame {self.frame_count} no tiene datos SRT. Frame omitido.')
            return

        current_time = self.get_clock().now().to_msg()

        # Imagen raw
        img_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        img_msg.header.stamp = current_time
        img_msg.header.frame_id = self.CAMERA_FRAME_ID
        self.pub_image_raw.publish(img_msg)

        # Imagen comprimida (JPEG)
        if self.use_compression:
            ok, buffer = cv2.imencode(
                '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
            )
            if ok:
                compressed_msg = CompressedImage()
                compressed_msg.header.stamp = current_time
                compressed_msg.header.frame_id = self.CAMERA_FRAME_ID
                compressed_msg.format = 'jpeg'
                compressed_msg.data = buffer.tobytes()
                self.pub_image_compressed.publish(compressed_msg)

        # Telemetria del dron
        drone_state = DroneState()
        drone_state.timestamp = current_time
        drone_state.latitude = drone_frame.latitude
        drone_state.longitude = drone_frame.longitude
        drone_state.altitude_rel = drone_frame.altitude_rel
        drone_state.altitude_abs = drone_frame.altitude_abs
        drone_state.yaw = drone_frame.yaw
        drone_state.pitch = drone_frame.pitch
        drone_state.roll = drone_frame.roll
        drone_state.focal_len = drone_frame.focal_len
        drone_state.dzoom_ratio = drone_frame.dzoom_ratio
        self.pub_drone_state.publish(drone_state)

        # Log de progreso cada 100 frames
        if self.frame_count % 100 == 0:
            progress = (self.frame_count / self.total_frames) * 100
            self.get_logger().info(
                f'Frame {self.frame_count}/{self.total_frames} ({progress:.1f}%) | '
                f'GPS: ({drone_frame.latitude:.6f}, {drone_frame.longitude:.6f})'
            )


def main(args=None):
    rclpy.init(args=args)
    node = VideoPublisherNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Detenido por el usuario.')
    finally:
        if hasattr(node, 'cap') and node.cap is not None:
            node.cap.release()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
