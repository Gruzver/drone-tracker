#!/usr/bin/env python3

"""
view_vision.py

Herramienta de diagnostico que muestra en una ventana OpenCV el video
anotado publicado por el nodo de deteccion YOLO.

Suscripciones:
    /vision/labeled_image_compressed (sensor_msgs/CompressedImage)

Uso:
    ros2 run yolo_detection_node view_vision

Presiona Q en la ventana para salir.
"""

import threading

import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import CompressedImage
from cv_bridge import CvBridge


class VisionViewer(Node):
    """
    Nodo de visualizacion que suscribe al topico de imagen comprimida anotada
    y la muestra en tiempo real en una ventana OpenCV.

    La recepcion de mensajes y la actualizacion de la ventana corren en hilos
    separados. Se usa threading.Event para señalizar la parada de forma segura.
    """

    WINDOW_NAME = 'Vision Labeled - Press Q to Exit'
    WINDOW_W = 800
    WINDOW_H = 640

    def __init__(self):
        super().__init__('vision_viewer')

        self.bridge = CvBridge()
        self.latest_frame = None
        self._stop_event = threading.Event()

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self.create_subscription(
            CompressedImage,
            '/vision/labeled_image_compressed',
            self._image_callback,
            qos,
        )

        self.get_logger().info('Mostrando video en vivo. Presiona Q para salir.')

        self._display_thread = threading.Thread(
            target=self._display_loop, daemon=True
        )
        self._display_thread.start()

    def _image_callback(self, msg: CompressedImage) -> None:
        """Decodifica el mensaje comprimido y actualiza el frame en memoria."""
        try:
            self.latest_frame = self.bridge.compressed_imgmsg_to_cv2(
                msg, desired_encoding='bgr8'
            )
        except Exception as e:
            self.get_logger().error('Error decodificando imagen comprimida: %s', str(e))

    def _display_loop(self) -> None:
        """
        Bucle de renderizado en un hilo dedicado para no bloquear el spin ROS.

        Muestra el ultimo frame disponible y espera la tecla Q para señalizar
        la parada mediante el evento de parada compartido.
        """
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.WINDOW_NAME, self.WINDOW_W, self.WINDOW_H)

        while not self._stop_event.is_set():
            if self.latest_frame is not None:
                cv2.imshow(self.WINDOW_NAME, self.latest_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q')):
                self.get_logger().info('Cerrando visor.')
                self._stop_event.set()
                break

        cv2.destroyAllWindows()

    def stop(self) -> None:
        """Señaliza el hilo de display para que termine ordenadamente."""
        self._stop_event.set()


def main(args=None):
    rclpy.init(args=args)
    node = VisionViewer()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
