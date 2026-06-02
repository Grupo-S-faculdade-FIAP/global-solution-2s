"""
Módulo de inferência para detecção de tempestades com YOLOv8.

Classes:
    StormDetector: Classe principal para fazer predições com o modelo YOLO
    DetectionResult: Resultado de uma predição

Exemplo:
    detector = StormDetector(model_path="models/yolov8-storm-detector/weights/best.pt")
    results = detector.predict("path/to/image.jpg")
    print(results.detections)
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """Representa uma detecção de tempestade."""
    x: float  # Centro X em pixels
    y: float  # Centro Y em pixels
    width: float  # Largura da bbox em pixels
    height: float  # Altura da bbox em pixels
    confidence: float  # Confiança da detecção (0-1)
    class_name: str  # Nome da classe ("storm")


@dataclass
class DetectionResult:
    """Resultado de uma predição."""
    image_path: str
    num_detections: int
    detections: List[Detection]
    has_storm: bool  # True se confiança >= threshold
    average_confidence: float
    timestamp: str


class StormDetector:
    """
    Detector de tempestades usando YOLOv8.

    Atributos:
        model: Modelo YOLO carregado
        confidence_threshold: Limiar de confiança mínima (0-1)
        device: Device para inferência ('cpu' ou GPU index)
    """

    def __init__(
        self,
        model_path: str = "models/yolov8-storm-detector/weights/best.pt",
        confidence_threshold: float = 0.5,
        device: str = "cpu",
    ):
        """
        Inicializa o detector.

        Args:
            model_path: Caminho para o arquivo .pt do modelo
            confidence_threshold: Limiar mínimo de confiança
            device: 'cpu' ou índice da GPU
        """
        if YOLO is None:
            raise RuntimeError(
                "ultralytics não está instalado. Execute: pip install ultralytics"
            )

        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device = device

        # Carregar modelo
        logger.info(f"Carregando modelo: {model_path}")
        try:
            self.model = YOLO(model_path)
            self.model.to(device)
            logger.info(f"✅ Modelo carregado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo: {e}")
            raise

    def predict(self, image_path: str) -> DetectionResult:
        """
        Faz predição em uma imagem.

        Args:
            image_path: Caminho da imagem ou URL

        Returns:
            DetectionResult com detecções e metadados
        """
        logger.info(f"Predizendo: {image_path}")

        try:
            # Rodar inferência
            results = self.model.predict(
                source=image_path,
                conf=self.confidence_threshold,
                verbose=False,
            )

            detections = []
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        x, y, w, h = box.xywh[0].cpu().numpy()
                        conf = box.conf[0].item()
                        class_id = int(box.cls[0].item())
                        class_name = result.names[class_id]

                        detections.append(
                            Detection(
                                x=float(x),
                                y=float(y),
                                width=float(w),
                                height=float(h),
                                confidence=float(conf),
                                class_name=class_name,
                            )
                        )

            # Calcular métricas
            has_storm = len(detections) > 0
            avg_conf = (
                np.mean([d.confidence for d in detections])
                if detections
                else 0.0
            )

            result = DetectionResult(
                image_path=image_path,
                num_detections=len(detections),
                detections=detections,
                has_storm=has_storm,
                average_confidence=float(avg_conf),
                timestamp=datetime.now().isoformat(),
            )

            logger.info(
                f"✅ Predição concluída: {len(detections)} detecções encontradas"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Erro durante predição: {e}")
            return DetectionResult(
                image_path=image_path,
                num_detections=0,
                detections=[],
                has_storm=False,
                average_confidence=0.0,
                timestamp=datetime.now().isoformat(),
            )

    def predict_batch(self, image_paths: List[str]) -> List[DetectionResult]:
        """
        Faz predições em múltiplas imagens.

        Args:
            image_paths: Lista de caminhos de imagens

        Returns:
            Lista de DetectionResult
        """
        results = []
        for img_path in image_paths:
            result = self.predict(img_path)
            results.append(result)
        return results

    def predict_with_visualization(
        self, image_path: str, output_path: Optional[str] = None
    ) -> Tuple[DetectionResult, np.ndarray]:
        """
        Faz predição e retorna imagem com bounding boxes desenhadas.

        Args:
            image_path: Caminho da imagem
            output_path: Caminho para salvar imagem com visualização (opcional)

        Returns:
            Tupla (DetectionResult, imagem com boxes)
        """
        # Fazer predição
        result = self.predict(image_path)

        # Carregar imagem
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Não conseguiu carregar imagem: {image_path}")
            return result, np.array([])

        # Desenhar bounding boxes
        for detection in result.detections:
            x_center, y_center = int(detection.x), int(detection.y)
            width, height = int(detection.width), int(detection.height)
            x_min = x_center - width // 2
            y_min = y_center - height // 2
            x_max = x_center + width // 2
            y_max = y_center + height // 2

            # Cor baseada em confiança (verde-amarelo-vermelho)
            conf = detection.confidence
            if conf > 0.8:
                color = (0, 255, 0)  # Verde
            elif conf > 0.6:
                color = (0, 255, 255)  # Amarelo
            else:
                color = (0, 0, 255)  # Vermelho

            # Desenhar bbox
            cv2.rectangle(image, (x_min, y_min), (x_max, y_max), color, 2)

            # Desenhar label
            label = f"{detection.class_name} {conf:.2f}"
            cv2.putText(
                image,
                label,
                (x_min, y_min - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )

        # Salvar se solicitado
        if output_path:
            cv2.imwrite(output_path, image)
            logger.info(f"Imagem salva: {output_path}")

        return result, image

    def get_model_info(self) -> Dict:
        """Retorna informações sobre o modelo."""
        return {
            "model_path": self.model_path,
            "device": self.device,
            "confidence_threshold": self.confidence_threshold,
            "model_size": self.model.model.parameters.__len__(),
            "model_summary": str(self.model.model),
        }
