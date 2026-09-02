import os
import sys
from pathlib import Path

# Add server directory to python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Isolate vector store database to test data directory
os.environ["VECTOR_STORE_DIR"] = str(Path(__file__).parent / "test_data_validation")

import services.vector_store as vs

# 1. Define the Golden Dataset (Ground Truth Emails)
GOLDEN_DOCUMENTS = [
    {
        "message_id": "gold_msg_billing",
        "from": "finance@figmalabs.com",
        "subject": "Figma Labs Invoice Q3-2026",
        "date": "2026-08-10",
        "summary": "This document contains details regarding Figma Labs' Q3 cloud billing. The invoice total is $12,450, due on September 1st, 2026. Send payment to widgets-hq account."
    },
    {
        "message_id": "gold_msg_api_bug",
        "from": "dev-leads@scaletechnologies.com",
        "subject": "Production API Timeout Error",
        "date": "2026-08-12",
        "summary": "We are experiencing a 504 gateway timeout bug on the /v1/sync endpoint. This happens when client request size exceeds 50MB. Need immediate hotfix."
    },
    {
        "message_id": "gold_msg_recruitment",
        "from": "hr@widgets.com",
        "subject": "Candidate selection for Frontend Role",
        "date": "2026-08-14",
        "summary": "Resume screening results for the Senior React developer role. Selected Alice Smith for round-2 interview based on her expertise in styled-components and state management."
    },
    {
        "message_id": "gold_msg_grievance",
        "from": "grievous_customer@scaletechnologies.com",
        "subject": "Complaint regarding service down-time",
        "date": "2026-08-15",
        "summary": "Extremely unsatisfied with the 4-hour server outage last Tuesday. Our operations were completely halted. Requesting a 15% service credit reimbursement."
    },
    {
        "message_id": "gold_msg_security",
        "from": "security-alerts@cloudflare.com",
        "subject": "Potential DDoS attack mitigated",
        "date": "2026-08-16",
        "summary": "Cloudflare Web Application Firewall detected and mitigated a high-volume volumetric layer 7 DDoS attack targeting widgets domain. No downtime occurred."
    }
]

# 2. Define Golden Queries mapped to Expected Best Match IDs
GOLDEN_QUERIES = [
    {
        "query": "invoice cloud billing payment due",
        "expected_id": "gold_msg_billing",
        "description": "Financial / Invoice search"
    },
    {
        "query": "gateway timeout error on production api sync",
        "expected_id": "gold_msg_api_bug",
        "description": "Tech support / bug reporting"
    },
    {
        "query": "selected React candidate interview senior frontend developer",
        "expected_id": "gold_msg_recruitment",
        "description": "Recruiting / Resume screening"
    },
    {
        "query": "complain server outage downtime credit request",
        "expected_id": "gold_msg_grievance",
        "description": "Grievance / customer dissatisfaction"
    },
    {
        "query": "ddos volumetric layer 7 cloudflare attack target",
        "expected_id": "gold_msg_security",
        "description": "Security warning alerts"
    }
]

def run_retrieval_validation():
    print("==================================================================")
    print("       NEXUSOPSCRM GOLDEN DATASET RETRIEVAL VALIDATION            ")
    print("==================================================================")
    
    # Reset vector store to fresh test location
    vs._metadata = []
    vs._index = None
    vs.load_store()
    
    # Index the Golden Dataset
    print(f"Indexing {len(GOLDEN_DOCUMENTS)} Golden Documents...")
    for doc in GOLDEN_DOCUMENTS:
        vs.add_document(doc)
    print("Indexing completed successfully.\n")
    
    passed_tests = 0
    total_tests = len(GOLDEN_QUERIES)
    rr_sum = 0.0 # Reciprocal Rank sum for MRR calculation
    
    print(f"{'Query Description':<30} | {'Expected ID':<18} | {'Best Match ID':<18} | {'Score':<6} | {'Result':<6}")
    print("-" * 92)
    
    for test in GOLDEN_QUERIES:
        query = test["query"]
        expected_id = test["expected_id"]
        desc = test["description"]
        
        # Search the top-3 results
        results = vs.search(query, k=3)
        
        best_match_id = "None"
        best_score = 0.0
        rank = 0
        
        # Check rank position of expected document
        for idx, res in enumerate(results):
            if res["message_id"] == expected_id:
                rank = idx + 1
                break
        
        if len(results) > 0:
            best_match_id = results[0]["message_id"]
            best_score = results[0]["score"]
            
        status = "FAIL"
        if best_match_id == expected_id:
            passed_tests += 1
            status = "PASS"
            
        reciprocal_rank = 1.0 / rank if rank > 0 else 0.0
        rr_sum += reciprocal_rank
        
        print(f"{desc:<30} | {expected_id:<18} | {best_match_id:<18} | {best_score:.3f} | {status:<6}")
        
    accuracy = (passed_tests / total_tests) * 100
    mrr = rr_sum / total_tests
    
    print("-" * 92)
    print(f"VAL ACCURACY (Top-1 Match): {accuracy:.1f}% ({passed_tests}/{total_tests})")
    print(f"MEAN RECIPROCAL RANK (MRR): {mrr:.3f}")
    print("==================================================================")
    
    # Tear down test data folder
    import shutil
    test_dir = Path(__file__).parent / "test_data_validation"
    if test_dir.exists():
        shutil.rmtree(test_dir)
        
    # Return exit code based on retrieval validation success
    if accuracy == 100.0:
        print("ALL RETRIEVAL VALIDATION TESTS PASSED (100% Accuracy)!")
        sys.exit(0)
    else:
        print("RETRIEVAL VALIDATION FAILED (Accuracy < 100%)!")
        sys.exit(1)

if __name__ == "__main__":
    run_retrieval_validation()
