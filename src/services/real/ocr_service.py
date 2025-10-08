import base64
import io
import os
import tempfile
import cv2
import pytesseract
import easyocr
import torch
import numpy as np
import logging
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration, logging as transformers_logging
from typing import Dict, Any, Optional, Tuple

from src.services.interfaces._ocr import OCRServiceInterface

log = logging.getLogger(__name__)

# Suppress verbose output from the transformers library
transformers_logging.set_verbosity_error()

class ModelManager:
    """Manages EAGER loading of resource-intensive AI models."""
    def __init__(self):
        self._easyocr_reader: Optional[easyocr.Reader] = None
        self._blip_processor: Optional[BlipProcessor] = None
        self._blip_model: Optional[BlipForConditionalGeneration] = None
        
        # Eagerly load all models when the manager is created.
        self.load_all_models()

    def load_all_models(self):
        """Loads all necessary models at once."""
        self.get_easyocr_reader()
        self.get_blip_model()

    def get_easyocr_reader(self) -> Optional[easyocr.Reader]:
        if self._easyocr_reader is None:
            log.info("Initializing EasyOCR reader...")
            try:
                # Define a persistent cache directory for OCR models
                ocr_model_dir = "/tmp/models/.cache/easyocr/"
                os.makedirs(ocr_model_dir, exist_ok=True)
                
                # Tell EasyOCR to use our persistent directory
                self._easyocr_reader = easyocr.Reader(
                    ["en"], 
                    gpu=torch.cuda.is_available(), 
                    verbose=False,
                    model_storage_directory=ocr_model_dir
                )
                log.info(f"EasyOCR reader initialized successfully. Models are cached in {ocr_model_dir}")
            except Exception as e:
                log.error(f"Failed to initialize EasyOCR: {e}", exc_info=True)
                self._easyocr_reader = None
        return self._easyocr_reader

    def get_blip_model(self) -> Tuple[Optional[BlipProcessor], Optional[BlipForConditionalGeneration]]:
        if self._blip_processor is None or self._blip_model is None:
            log.info("Initializing BLIP image captioning models...")
            model_name = "Salesforce/blip-image-captioning-base"
            try:
                # This will also use the default Hugging Face cache, which can be made persistent.
                self._blip_processor = BlipProcessor.from_pretrained(model_name)
                self._blip_model = BlipForConditionalGeneration.from_pretrained(model_name)
                log.info("BLIP models initialized successfully.")
            except Exception as e:
                log.error(f"Failed to initialize BLIP models: {e}", exc_info=True)
                self._blip_processor = None
                self._blip_model = None
        return self._blip_processor, self._blip_model

class ImageHandler:
    """Handles all image processing tasks including OCR and captioning."""
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager

    def _preprocess_image(self, img_array: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        
        # Deskewing logic
        coords = np.column_stack(np.where(gray > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        (h, w) = gray.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        deskewed = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        # Denoising and Binarization
        denoised = cv2.fastNlMeansDenoising(deskewed, h=10)
        binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        return binary

    def run_tesseract(self, img_array: np.ndarray) -> Dict[str, Any]:
        config = "--oem 3 --psm 6"
        try:
            data = pytesseract.image_to_data(img_array, lang="eng", config=config, output_type=pytesseract.Output.DICT)
            text = " ".join([word for word in data["text"] if word.strip()])
            conf_list = [float(c) for c in data["conf"] if float(c) > 0]
            avg_conf = sum(conf_list) / len(conf_list) if conf_list else 0.0
            return {"text": text, "conf": avg_conf}
        except Exception as e:
            log.error(f"Tesseract OCR failed: {e}")
            return {"text": "", "conf": 0}

    def run_easyocr(self, img_array: np.ndarray) -> Dict[str, Any]:
        reader = self.model_manager.get_easyocr_reader()
        if not reader:
            return {"text": "EasyOCR not initialized", "conf": 0}
        try:
            results = reader.readtext(img_array)
            if not results:
                return {"text": "", "conf": 0.0}
            texts = [item[1] for item in results]
            confs = [item[2] for item in results]
            avg_conf = sum(confs) / len(confs) if confs else 0.0
            return {"text": " ".join(texts), "conf": avg_conf}
        except Exception as e:
            log.error(f"EasyOCR failed: {e}")
            return {"text": "", "conf": 0}

    def generate_caption(self, img_array: np.ndarray) -> str:
        """Generate a descriptive caption for an image using the BLIP model."""
        processor, model = self.model_manager.get_blip_model()
        if not processor or not model:
            return "Captioning model not initialized."
        
        try:
            # Convert cv2 image to PIL Image
            img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            
            inputs = processor(images=pil_img, return_tensors="pt")
            
            # Generate caption
            output_ids = model.generate(**inputs, max_new_tokens=30)
            caption = processor.batch_decode(output_ids, skip_special_tokens=True)[0].strip()
            
            return caption
        except Exception as e:
            log.error(f"Caption generation failed: {e}")
            return "Error during caption generation."

    def process_image_array(self, img_array: np.ndarray) -> Dict[str, Any]:
        """Processes a cv2 image array and returns OCR text and caption."""
        preprocessed_img = self._preprocess_image(img_array)
        tess_res = self.run_tesseract(preprocessed_img)
        easy_res = self.run_easyocr(img_array)
        
        best_ocr = tess_res if tess_res["conf"] >= easy_res["conf"] else easy_res
        caption = self.generate_caption(img_array)
        
        log.info(f"OCR completed. Winning engine: {'Tesseract' if best_ocr is tess_res else 'EasyOCR'}")
        
        return {
            "text": best_ocr.get("text", ""),
            "confidence": best_ocr.get("conf", 0),
            "caption": caption,
            "tesseract_result": tess_res,
            "easyocr_result": easy_res
        }

class RealOCRService(OCRServiceInterface):
    """Main OCR Service that uses the ImageHandler logic."""
    def __init__(self):
        log.info("--- [RealOCRService] Initializing OCR Models via ModelManager ---")
        self.model_manager = ModelManager()
        self.image_handler = ImageHandler(self.model_manager)
        log.info("--- [RealOCRService] OCR Service Ready ---")

    async def extract_text_from_image(self, image_data: str) -> str:
        """Decodes a base64 image and processes it using ImageHandler."""
        try:
            if "," in image_data:
                _, encoded = image_data.split(",", 1)
            else:
                encoded = image_data
            
            image_bytes = base64.b64decode(encoded)
            image_array = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if img is None:
                raise ValueError("Could not decode image.")

            log.info("Extracting text with Real OCR Service...")
            result = self.image_handler.process_image_array(img)
            log.info("Text extraction successful.")
            
            return result["text"]

        except Exception as e:
            log.error(f"Error during OCR processing: {e}", exc_info=True)
            return "Error: Could not process the image."

    async def process_image_with_caption(self, image_data: str) -> Dict[str, Any]:
        """Process image to extract both text and generate caption."""
        try:
            if "," in image_data:
                _, encoded = image_data.split(",", 1)
            else:
                encoded = image_data
            
            image_bytes = base64.b64decode(encoded)
            image_array = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if img is None:
                raise ValueError("Could not decode image.")

            log.info("Processing image with OCR and captioning...")
            result = self.image_handler.process_image_array(img)
            log.info("Image processing successful.")
            
            return result

        except Exception as e:
            log.error(f"Error during image processing: {e}", exc_info=True)
            return {
                "text": "Error: Could not process the image.",
                "confidence": 0,
                "caption": "Error during processing",
                "tesseract_result": {"text": "", "conf": 0},
                "easyocr_result": {"text": "", "conf": 0}
            }
