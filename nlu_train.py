import random
from pathlib import Path
import spacy
from spacy.training.example import Example
from spacy.util import minibatch, compounding

# Training data: texts + intent labels
TRAIN_DATA = [
    ("I want to book an appointment", {"cats": {"book_appointment": 1.0, "cancel_appointment": 0.0, "greeting": 0.0}}),
    ("Please schedule my cleaning", {"cats": {"book_appointment": 1.0, "cancel_appointment": 0.0, "greeting": 0.0}}),
    ("Cancel my visit tomorrow", {"cats": {"book_appointment": 0.0, "cancel_appointment": 1.0, "greeting": 0.0}}),
    ("Hey there!", {"cats": {"book_appointment": 0.0, "cancel_appointment": 0.0, "greeting": 1.0}}),
    ("Good morning", {"cats": {"book_appointment": 0.0, "cancel_appointment": 0.0, "greeting": 1.0}}),
    ("I need to cancel my checkup", {"cats": {"book_appointment": 0.0, "cancel_appointment": 1.0, "greeting": 0.0}}),
    ("Book me for a dentist visit on Friday", {"cats": {"book_appointment": 1.0, "cancel_appointment": 0.0, "greeting": 0.0}}),
]

def train(n_iter: int = 20):
    # Create blank English model
    nlp = spacy.blank("en")

    # Add text classifier pipe
    if "textcat" not in nlp.pipe_names:
        textcat = nlp.add_pipe("textcat_multilabel", last=True)
    else:
        textcat = nlp.get_pipe("textcat")

    # Add labels
    for _, annotations in TRAIN_DATA:
        for label in annotations["cats"]:
            textcat.add_label(label)

    optimizer = nlp.begin_training()
    print("Training the intent classifier...")

    for i in range(n_iter):
        random.shuffle(TRAIN_DATA)
        losses = {}
        batches = minibatch(TRAIN_DATA, size=compounding(4.0, 32.0, 1.5))

        for batch in batches:
            examples = []
            for text, annotations in batch:
                doc = nlp.make_doc(text)
                examples.append(Example.from_dict(doc, annotations))
            nlp.update(examples, sgd=optimizer, drop=0.2, losses=losses)

        print(f"Iteration {i+1}/{n_iter}, Loss: {losses.get('textcat_multilabel', 0):.3f}")

    output_dir = Path("nlu_model")
    nlp.to_disk(output_dir)
    print(f"✅ Model saved to {output_dir}")

def predict(text: str):
    nlp = spacy.load("nlu_model")
    doc = nlp(text)
    print(f"Text: {text}")
    print(f"Intent scores: {doc.cats}")
    return doc.cats

if __name__ == "__main__":
    train(20)
    predict("Can you book my appointment for Monday?")
