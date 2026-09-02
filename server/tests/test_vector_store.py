import services.vector_store as vs


def test_vector_store_fresh_state():
    vs._metadata = []
    vs._index = None
    vs.load_store()
    
    # Assert fresh index initialized
    assert len(vs._metadata) == 0
    assert vs._get_index().ntotal == 0

def test_add_document_and_search():
    vs._metadata = []
    vs._index = None
    vs.load_store()
    
    # Insert test email summary
    metadata = {
        "summary": "This is a contract discussion about cloud billing integration for widgets.",
        "message_id": "test_msg_1",
        "subject": "Billing discussion",
        "from": "accounting@widgets.com",
        "date": "2026-08-17"
    }
    
    doc_id = vs.add_document(metadata)
    assert doc_id is not None
    assert len(vs._metadata) == 1
    assert vs._metadata[0]["message_id"] == "test_msg_1"
    
    # Check that sender/email ID was prepended to summary
    assert "Sender/Email ID: accounting@widgets.com" in vs._metadata[0]["summary"]
    
    # Perform Search
    results = vs.search("widgets billing contract", k=1)
    assert len(results) == 1
    assert results[0]["message_id"] == "test_msg_1"
    assert results[0]["score"] >= 0.48
