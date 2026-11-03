import sys
import os
import django

# Setup Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'janasahayak.settings')
django.setup()

from core.services.matcher import calculate_match_score

def test_document_matching():
    # User has "Aadhaar Card" and "Marksheet"
    user = {
        "education_level": "ug",
        "income": 100000,
        "category": "general",
        "state": "odisha",
        "age": 20,
        "available_documents": ["Aadhaar Card", "Marksheet"]
    }
    
    # Scheme requires "Aadhar Card" and "10th Mark Sheet"
    scheme = {
        "name": "Test Scheme",
        "education_min": 0,
        "education_max": 5,
        "category": "all",
        "state": "all",
        "required_documents": ["Aadhar Card", "10th Mark Sheet"]
    }
    
    score, reasons, missing_docs, status = calculate_match_score(user, scheme)
    
    print(f"Score: {score}")
    print(f"Missing Documents: {missing_docs}")
    
    if not missing_docs:
        print("SUCCESS: Fuzzy matching worked!")
    else:
        print("FAILURE: Documents still missing.")

if __name__ == "__main__":
    test_document_matching()
