from sentence_transformers import SentenceTransformer
import torch
import time
import sys

model_name = "intfloat/multilingual-e5-small"

print(f"--- Diagnostic Script Started ---")
print(f"Model: {model_name}")
print(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")

start_time = time.time()
try:
    print("Step 1: Initializing SentenceTransformer (this may take time if downloading)...")
    model = SentenceTransformer(model_name)
    print(f"Step 2: Model loaded successfully in {time.time() - start_time:.2f} seconds!")

    print("Step 3: Testing a simple encode...")
    vec = model.encode("Hello world")
    print(f"Step 4: Encoding successful! Vector shape: {vec.shape}")

    print("--- Diagnostic SUCCESS ---")
    sys.exit(0)
except Exception as e:
    print(f"--- Diagnostic FAILED ---")
    print(f"Error: {e}")
    sys.exit(1)
