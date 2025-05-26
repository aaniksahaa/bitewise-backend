import json
import os
from app.db.session import SessionLocal
from app.models.llm_model import LLMModel

def seed_llm_models():
    json_path = os.path.join(os.path.dirname(__file__), "llm_models.json")
    with open(json_path, "r") as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        for entry in data:
            # Avoid duplicates (optional)
            exists = db.query(LLMModel).filter_by(
                model_name=entry["model_name"],
                provider_name=entry["provider_name"]
            ).first()
            if not exists:
                db.add(LLMModel(**entry))
        db.commit()
        print("Seeded llm_models table.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_llm_models() 