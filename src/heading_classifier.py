# Copy the HeadingClassifier from Challenge 1A
import joblib
import numpy as np
from typing import List, Dict

class HeadingClassifier:
    def __init__(self, model_path: str, scaler_path: str):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.model = None
        self.scaler = None
    
    def load_model(self):
        """Loads the trained model and scaler from disk."""
        try:
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            print(f"Model loaded from {self.model_path}")
            print(f"Scaler loaded from {self.scaler_path}")
            return True
        except FileNotFoundError as e:
            print(f"Error: Model or scaler file not found: {e}")
            print("Please ensure you have trained the model using train_model.py and saved it.")
            return False
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def predict_heading_levels(self, spans_data):
        """
        Predicts the heading level for a list of text spans.
        Returns a list of predicted labels (strings).
        """
        if self.model is None or self.scaler is None:
            print("Model not loaded. Call load_model() first.")
            return []

        if not spans_data:
            return []

        try:
            # Convert spans data to DataFrame of features
            features_df = self.feature_extractor.spans_to_dataframe(spans_data)

            # Ensure feature columns match training order
            expected_columns = self.feature_extractor.get_feature_columns()
            
            if list(features_df.columns) != expected_columns:
                print("Warning: Feature columns mismatch. Ensuring correct order.")
                missing_cols = set(expected_columns) - set(features_df.columns)
                extra_cols = set(features_df.columns) - set(expected_columns)
                if missing_cols:
                    print(f"Missing columns: {missing_cols}")
                if extra_cols:
                    print(f"Extra columns: {extra_cols}")
                features_df = features_df[expected_columns]

            # Scale features
            features_scaled = self.scaler.transform(features_df)

            # Make predictions
            predictions = self.model.predict(features_scaled)

            # Convert numeric predictions back to labels
            predicted_labels = [self.rev_label_map.get(pred, "Body Text") for pred in predictions]

            return predicted_labels

        except Exception as e:
            print(f"Error during prediction: {e}")
            import traceback
            traceback.print_exc()
            return ["Body Text"] * len(spans_data)  # Fallback to body text
