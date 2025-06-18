from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class IntentClassifier:
    def __init__(self, model_path=r"/Users/harshvardhan/RagChatbot/fine_tuned_model"):
        self.id2label = {0: "Q&A", 1: "Summarize Full Document"}
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.eval()

    def predict_intent(self, query: str) -> str:
        inputs = self.tokenizer(query, return_tensors="pt", truncation=True, padding=True, max_length=128)
        with torch.no_grad():
            outputs = self.model(**inputs)
            predicted_class = torch.argmax(outputs.logits, dim=1).item()
        return self.id2label[predicted_class]
