from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from datasets import load_dataset
from sklearn.metrics import accuracy_score, f1_score

# Load CSV dataset
data = load_dataset('csv', data_files=r'/Users/harshvardhan/RagChatbot/query_classification_dataset_1000.csv')
raw_dataset = data[list(data.keys())[0]]  # usually 'train'

# Define only 2 labels
label2id = {"Q&A": 0, "Summarize Full Document": 1}
id2label = {v: k for k, v in label2id.items()}

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')

# Tokenization function
def tokenize(example):
    example["labels"] = label2id[example["label"]]
    return tokenizer(example["text"], truncation=True, padding="max_length", max_length=128)

# Split into train/test
split_dataset = raw_dataset.train_test_split(test_size=0.2, seed=42)

# Tokenize both train and test
tokenized_dataset = split_dataset.map(tokenize)
tokenized_dataset.set_format(type="torch", columns=["input_ids", "attention_mask", "labels"])

# Load model for 2-label classification
model = AutoModelForSequenceClassification.from_pretrained(
    'distilbert-base-uncased',
    num_labels=2,
    id2label=id2label,
    label2id=label2id
)

# Define metrics
def compute_metrics(p):
    preds = p.predictions.argmax(-1)
    labels = p.label_ids
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1": f1_score(labels, preds, average="weighted")
    }

# Training arguments
training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=4,
    per_device_train_batch_size=16,
    do_eval=True,
    logging_steps=50,
    save_steps=100,
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["test"],
    compute_metrics=compute_metrics
)

# Train
trainer.train()

# Save model and tokenizer
model.save_pretrained('./fine_tuned_model')
tokenizer.save_pretrained('./fine_tuned_model')
