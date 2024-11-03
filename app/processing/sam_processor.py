import torch
from segment_anything import sam_model_registry, SamPredictor

class SAMProcessor:
    def __init__(self, model_path):
        self.model_path = model_path
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.sam = None
        self.predictor = None
    
    def load_model(self):
        """Load the SAM model and return success status"""
        try:
            # Initialize SAM
            model_type = "vit_h"
            self.sam = sam_model_registry[model_type](checkpoint=self.model_path)
            self.sam.to(device=self.device)
            
            # Initialize predictor
            self.predictor = SamPredictor(self.sam)
            
            return True, "Model loaded successfully"
        except Exception as e:
            return False, f"Error loading model: {str(e)}"
    
    def is_model_loaded(self):
        """Check if model is loaded"""
        return self.sam is not None and self.predictor is not None