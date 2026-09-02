import datetime
import json
import os
from threading import Lock

import httpx

TRACKED_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tracked_threads.json")
_lock = Lock()

def track_thread(uid: str, thread_id: str, to_email: str, subject: str):
    """
    Register a newly sent thread for reply tracking.
    """
    os.makedirs(os.path.dirname(TRACKED_FILE), exist_ok=True)
    entry = {
        "uid": uid,
        "thread_id": thread_id,
        "to_email": to_email,
        "subject": subject,
        "sent_time": datetime.datetime.utcnow().isoformat() + "Z",
        "has_reply": False,
        "dismissed": False,
        "reply_from": "",
        "reply_snippet": "",
        "notified": False,
        "last_notified_msg_id": ""
    }

    with _lock:
        threads = []
        if os.path.exists(TRACKED_FILE):
            try:
                with open(TRACKED_FILE, "r", encoding="utf-8") as f:
                    threads = json.load(f)
            except Exception:
                threads = []
        
        # Avoid duplicate tracking
        if not any(t.get("thread_id") == thread_id for t in threads):
            threads.append(entry)
            try:
                with open(TRACKED_FILE, "w", encoding="utf-8") as f:
                    json.dump(threads, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[ReplyTracker] Failed to write tracked thread: {e}")

async def check_for_replies(access_token: str, uid: str, user_email: str) -> list[dict]:
    """
    Scan all active tracked threads for new messages sent by the recipient.
    Returns a list of threads that have new, undismissed replies.
    """
    if not os.path.exists(TRACKED_FILE):
        return []

    with _lock:
        try:
            with open(TRACKED_FILE, "r", encoding="utf-8") as f:
                threads = json.load(f)
        except Exception:
            return []

    user_threads = [t for t in threads if t.get("uid") == uid]
    if not user_threads:
        print(f"[ReplyTracker] No tracked threads found to check for user: {user_email}")
        return []

    updated = False
    alerts = []

    async with httpx.AsyncClient() as client:
        for t in user_threads:
            thread_id = t["thread_id"]
            try:
                resp = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                if resp.status_code == 200:
                    thread_data = resp.json()
                    messages = thread_data.get("messages", [])
                    
                    # Search messages in reverse order to find the LATEST reply from recipient
                    latest_reply_msg = None
                    for msg in reversed(messages):
                        headers = msg.get("payload", {}).get("headers", [])
                        msg_from = next((h.get("value", "") for h in headers if h.get("name", "").lower() == "from"), "")
                        
                        msg_email = msg_from
                        if "<" in msg_from and ">" in msg_from:
                            msg_email = msg_from.split("<")[1].split(">")[0]
                        
                        clean_msg_email = msg_email.lower().strip()
                        clean_user_email = user_email.lower().strip()
                        
                        if clean_msg_email != clean_user_email:
                            latest_reply_msg = msg
                            latest_reply_from = msg_from
                            break
                    
                    if latest_reply_msg:
                        latest_msg_id = latest_reply_msg.get("id")
                        last_notified = t.get("last_notified_msg_id", "")
                        
                        # If this is a new reply we haven't notified yet
                        if latest_msg_id != last_notified:
                            print(f"[ReplyTracker] New reply detected in thread {thread_id}! Message ID: {latest_msg_id}")
                            import re
                            raw_snippet = latest_reply_msg.get("snippet", "")
                            parts = re.split(r'\s*\bOn\s+.*?\s+wrote:', raw_snippet, flags=re.IGNORECASE)
                            
                            t["reply_snippet"] = parts[0].strip() if parts else raw_snippet
                            t["reply_from"] = latest_reply_from
                            t["has_reply"] = True
                            t["dismissed"] = False # Wake alert up!
                            t["last_notified_msg_id"] = latest_msg_id
                            updated = True
            except Exception as e:
                print(f"[ReplyTracker] Error checking thread {thread_id}: {e}")

            if t.get("has_reply") and not t.get("dismissed"):
                alerts.append(t)

    # Save updates back to disk
    if updated:
        with _lock:
            try:
                with open(TRACKED_FILE, "r", encoding="utf-8") as f:
                    all_threads = json.load(f)
                
                # Update records in the complete list
                for thread in all_threads:
                    for ut in user_threads:
                        if thread["thread_id"] == ut["thread_id"]:
                            thread["has_reply"] = ut["has_reply"]
                            thread["reply_from"] = ut["reply_from"]
                            thread["reply_snippet"] = ut["reply_snippet"]
                            thread["dismissed"] = ut["dismissed"]
                            thread["last_notified_msg_id"] = ut.get("last_notified_msg_id", "")
                
                with open(TRACKED_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_threads, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[ReplyTracker] Failed to update tracked threads file: {e}")

    return alerts

def dismiss_thread(uid: str, thread_id: str) -> bool:
    """
    Mark a thread's reply alert as dismissed.
    """
    if not os.path.exists(TRACKED_FILE):
        return False

    success = False
    with _lock:
        try:
            with open(TRACKED_FILE, "r", encoding="utf-8") as f:
                threads = json.load(f)
            
            for t in threads:
                if t.get("uid") == uid and t.get("thread_id") == thread_id:
                    t["dismissed"] = True
                    success = True
                    break
            
            if success:
                with open(TRACKED_FILE, "w", encoding="utf-8") as f:
                    json.dump(threads, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ReplyTracker] Failed to dismiss thread: {e}")
            return False

    return success
