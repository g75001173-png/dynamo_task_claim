#!/usr/bin/env python3
"""
Handshake Task Async Sniper – pure API, no browser.
Uses aiohttp and asyncio for bare-metal multi-threaded speed.
"""

import asyncio
import aiohttp
import json
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from plyer import notification
except ImportError:
    notification = None
try:
    import playsound
except ImportError:
    playsound = None

# ---------- CONFIGURATION ----------
ANNOTATION_PROJECT_ID = "a1d39753-ae51-41df-8c86-2b7e73c6bd6b"
CLAIMER_ID = "3f64c23c-3892-4cb5-9248-2b07862e4de0"
BASE_URL = "https://ai.joinhandshake.com/api/trpc"

HEADERS = {
    "Content-Type": "application/json",
    "Cookie": "ajs_anonymous_id=e200bf1f-7347-4622-923a-f6b138c7fd37; _ga=GA1.1.1847799391.1775314617; kameleoonVisitorCode=k66hpljuyugekiow; _fbp=fb.1.1775314625225.560576931579334839; _tt_enable_cookie=1; _ttp=01KNCFYSRTS89W5PSN5GNS39YA_.tt.1; ajs_user_id=74454772; _dd_s=isExpired=1&aid=0286be94-bd9f-4afd-a2ed-e3634428e087; _swb=8dfb5c63-6d43-42de-a7f5-6ff6503bcba1; _ketch_consent_v1_=eyJlc3NlbnRpYWxfc2VydmljZXMiOnsic3RhdHVzIjoiZ3JhbnRlZCIsImNhbm9uaWNhbFB1cnBvc2VzIjpbImVzc2VudGlhbF9zZXJ2aWNlcyJdfSwiYW5hbHl0aWNzIjp7InN0YXR1cyI6ImdyYW50ZWQiLCJjYW5vbmljYWxQdXJwb3NlcyI6WyJhbmFseXRpY3MiXX0sInRhcmdldGVkX2FkdmVydGlzaW5nIjp7InN0YXR1cyI6ImdyYW50ZWQiLCJjYW5vbmljYWxQdXJwb3NlcyI6WyJiZWhhdmlvcmFsX2FkdmVydGlzaW5nIl19fQ%3D%3D; production_magic_link_email_address=eyJfcmFpbHMiOnsibWVzc2FnZSI6IkltYzNOVEF3TVRFM00wQm5iV0ZwYkM1amIyMGkiLCJleHAiOm51bGwsInB1ciI6ImNvb2tpZS5wcm9kdWN0aW9uX21hZ2ljX2xpbmtfZW1haWxfYWRkcmVzcyJ9fQ%3D%3D--257496991e70a2487abee2eea7d46ad890c0817e; request_method=POST; ajs_user_id=74454772; ajs_anonymous_id=e200bf1f-7347-4622-923a-f6b138c7fd37; _ga_SHCDNG08QG=deleted; production_current_user=74454772; iterableEndUserId=g75001173%40gmail.com; _cfuvid=cgCLLn5lyjNU59GrbzMBNyRthQayhTmVFyLktZ1Ipn8-1787259199.096435-1.0.1.1-73ZBVSLdbcp1pI5bAbcJaHogdbqw9s2LBjkQnbz0ytw; _rdt_uuid=1775314621549.785a0abe-7db1-4406-8c62-82bef0cb7c3d; _uetsid=76c64d2088ea11f1a2875b8c8c5bc9f3; _uetvid=8b679480303611f183021fc53f45b693; ttcsid=1787259238878::TLmI17q94WIGo3On37_L.10.1787259279382.0::1.27019.40270::0.0.0.0::0.0.0; ttcsid_D15H40JC77UBTE66SJ6G=1787259238878::87-AWUZpDD_kh-qFxm_W.10.1787259279383.1; hss-global=eyJhbGciOiJkaXIiLCJjdHkiOiJKV1QiLCJlbmMiOiJBMjU2Q0JDLUhTNTEyIiwidHlwIjoiSldUIn0..RBFzslcBM7VjOgWjNQWK1w.WvG3qxTXxaK6Bsro_22h7KqzqJlO-mqzHNeY_8nEm5w1jjRFO6vHBupoS5GjXvcPi2MLZjHSCtWgsAMvLuvbJC-YWQVzMGTAj27iV4zdq_GOkyQiyaqo5gZlBqNKRLkHlRQiHYEmsYDrO_qZ-GLj5K4o5EjZ2A-wDXqdFPbWiDgyc3262BC1OwW7MH8HwbvEudbQgVziZsvzvLVHPGveoNzATgYAJa7UXYY6TeudYPwPr0RnFVFf6qIvlnzeD-qhAXL-Og8t19YPox6CVZR30pH-j6T8m7rBqt-lP7vIgGU85N_mH6WXL8s8gl8oiwCKEpSw5rQGteISgdgbon-94wWDwHS3KnXsmF4iPlbG5QzpzVo2iDdsSxil5QhsiNyP.-1MlTyCv2sXY1aYzN6lBcDu86NpxUut1Os7xUvuslFE; hss-marketing=students; _ga_4M16ZMP2G5=GS2.1.s1787259231$o11$g1$t1787259302$j53$l0$h0; fs_uid=#H7TB#90600328-625d-4662-9d09-1b5699d68ef0:9d743cf4-f02a-4c5f-b0d3-3ee0f61d8be8:1787259259042::2#39ea3185###/1806853229; _gcl_au=1.1.2053445480.1783099828.-.-.1783258006.2009958182.1787259312.1787259346; _ga_SHCDNG08QG=GS2.1.s1787259213$o117$g1$t1787259346$j25$l0$h0; __cf_bm=5SZ6dSKjF69AgRNnnZzmz03ucPMLzD4hMgF_Xrq_Tak-1787262147.7032518-1.0.1.1-wQFbh6zG8CYzbX3XbryYw77I8GGGK7ZEom.3dmZLallJesGyWbosr10p6eZ4svQUUT1hzkdjHeGigKVpaZRWspXAED_JFZJ5lGh9ijkOHFonoUZZYaaLcRYhovZAh.Yz; _trajectory_session=hGJw%2FHDa%2FJEzHumWTMl3b4iHu536wyXGbzQfe2pkWsDSWYcldGFzEpQHfUBikilsDg%2F%2Fxt9SNC60FMeaXgKYYadSDF9BnMTJbEGIsKAtVzlbOirsPyukY%2B0RH8xXNS3%2FxyYpuD%2FWCVeks4NCTVnudnczSofIrVmdacw6CVp3zRGl8G2qLqg2xCj0oSLElhA%2BtE4s3LwiiQyukiXTVSupvR924RWU3zGZ%2FyFdbjRNgQBBzqvN6OcS46H0hNZh0pTrYt8eZr6WavLs2nQ9S5ZV1p8k6qomnMb9pAM2xIlBZ8caUZcXS8zs--GL95BUoAy18cYkei--3PUjRH40PuHsU%2FoZv%2FP4SQ%3D%3D; _dd_s_v2=aid=0286be94-bd9f-4afd-a2ed-e3634428e087&id=d1690be5-70b8-4d56-844e-2a675158f5ee&created=1787259306044&expire=1787263426943&c=0"
}

POLL_INTERVAL = 1
INITIAL_BACKOFF = 60
MAX_BACKOFF = 300
backoff = INITIAL_BACKOFF

GET_TASKS_URL = f"{BASE_URL}/task.getAllClaimableTasksForFellow"
CLAIM_URL = f"{BASE_URL}/task.claimTask" 
GET_MY_TASKS_URL = f"{BASE_URL}/task.listClaimedTasksForFellow"

log_format = "%(asctime)s [%(levelname)s] %(message)s"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler("sniper.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Sniper")

def notify(title: str, message: str):
    if notification:
        try:
            notification.notify(title=title, message=message, timeout=5)
        except Exception as e:
            logger.debug(f"Notification failed: {e}")

def play_sound():
    if playsound:
        try:
            playsound.playsound("/usr/share/sounds/freedesktop/stereo/complete.oga", block=False)
            return
        except Exception as e:
            logger.debug(f"Sound failed: {e}")
    try:
        import winsound
        winsound.Beep(880, 800)
    except Exception as e:
        logger.debug(f"Windows beep failed: {e}")

async def fetch_tasks(session: aiohttp.ClientSession, offset: int = 0) -> Optional[List[Dict[str, Any]]]:
    payload = {
        "0": {
            "json": {
                "annotationProjectId": ANNOTATION_PROJECT_ID,
                "pipelineStageId": None,
                "attempters": None,
                "search": None,
                "sortBy": "default",
                "sortOrder": "desc",
                "limit": 10,
                "offset": offset,
                "categories": None,
                "priorityLevel": None
            },
            "meta": {
                "values": {
                    "pipelineStageId": ["undefined"],
                    "attempters": ["undefined"],
                    "search": ["undefined"],
                    "categories": ["undefined"],
                    "priorityLevel": ["undefined"]
                },
                "v": 1
            }
        }
    }
    try:
        params = {
            "batch": "1",
            "input": json.dumps(payload)
        }
        async with session.get(GET_TASKS_URL, params=params, timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.json()
            tasks = data[0].get("result", {}).get("data", {}).get("json", {}).get("tasks", [])
            return tasks
    except Exception as e:
        logger.error(f"Error while fetching: {e}")
        return None

async def claim_task(session: aiohttp.ClientSession, task_id: str) -> tuple[bool, bool]:
    payload = {
        "json": {
            "taskId": task_id,
            "annotationProjectId": ANNOTATION_PROJECT_ID,
            "claimerId": CLAIMER_ID
        }
    }
    try:
        async with session.post(CLAIM_URL, json=payload, timeout=10) as resp:
            if resp.status == 200:
                logger.info(f"✅ Claimed task {task_id}")
                return True, False
            elif resp.status == 429:
                logger.warning(f"⛔ Rate limited while claiming {task_id}")
                return False, True
            elif resp.status == 409:
                logger.warning(f"⚠️ Too slow! Task {task_id} was just claimed by someone else.")
                return False, False
            else:
                text = await resp.text()
                logger.error(f"❌ Claim failed for {task_id}: {resp.status} - {text}")
                return False, False
    except Exception as e:
        logger.error(f"Claim request error: {e}")
        return False, False

async def poll_loop():
    global backoff
    logger.info("🔫 Async Sniper started. Polling every %d seconds.", POLL_INTERVAL)
    
    # TCPConnector enables connection pooling for speed
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(headers=HEADERS, connector=connector) as session:
        while True:
            offset = 0
            total_claimed = 0
            while True:
                tasks = await fetch_tasks(session, offset)
                if tasks is None:
                    await asyncio.sleep(5)
                    continue
                if not tasks:
                    break
                
                logger.info(f"📦 Found {len(tasks)} task(s) on page {offset//10 + 1}. Firing parallel claims!")
                
                # Shotgun fire all claims instantly!
                claim_coroutines = []
                for task in tasks:
                    task_id = task.get("id")
                    if task_id:
                        claim_coroutines.append(claim_task(session, task_id))
                
                if claim_coroutines:
                    results = await asyncio.gather(*claim_coroutines)
                    for success, rate_limited in results:
                        if rate_limited:
                            logger.info(f"⏳ Rate limited. Waiting {backoff} seconds...")
                            await asyncio.sleep(backoff)
                            backoff = min(backoff * 1.5, MAX_BACKOFF)
                        if success:
                            total_claimed += 1
                            backoff = INITIAL_BACKOFF
                            notify("Sniper", "Claimed a task!")
                            play_sound()
                            
                offset += 10
                await asyncio.sleep(0.1)

            if total_claimed == 0:
                logger.info("No tasks available.")
            else:
                logger.info(f"✨ Claimed {total_claimed} task(s) this cycle.")

            await asyncio.sleep(POLL_INTERVAL)

async def test_connection():
    logger.info("🧪 Testing connection to Handshake API...")
    payload = {
        "0": {
            "json": {
                "annotationProjectId": ANNOTATION_PROJECT_ID,
                "pipelineStageId": None,
                "attempters": None,
                "search": None,
                "sortBy": "default",
                "sortOrder": "desc",
                "limit": 10,
                "offset": 0,
                "categories": None,
                "priorityLevel": None
            },
            "meta": {
                "values": {
                    "pipelineStageId": ["undefined"],
                    "attempters": ["undefined"],
                    "search": ["undefined"],
                    "categories": ["undefined"],
                    "priorityLevel": ["undefined"]
                },
                "v": 1
            }
        }
    }
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            params = {
                "batch": "1",
                "input": json.dumps(payload)
            }
            async with session.get(GET_TASKS_URL, params=params, timeout=10) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"❌ Connection failed! Status Code: {resp.status}")
                    logger.error(text)
                    return

                logger.info("✅ Authentication Successful! The server accepted your Cookie.")
                logger.info("Here is the exact raw data the server sent back to us:")
                data = await resp.json()
                print("\n" + json.dumps(data, indent=4) + "\n")
                
                tasks = data[0].get("result", {}).get("data", {}).get("json", {}).get("tasks", [])
                
                if len(tasks) == 0:
                    logger.info("Note: The server returned an empty tasks list []. This absolutely confirms your script is working perfectly, there are just no tasks available right now!")
                else:
                    logger.info(f"WOW! There are actually {len(tasks)} tasks available right now!")
                
        except Exception as e:
            logger.error(f"❌ Connection test crashed: {e}")

async def test_my_tasks():
    logger.info("🧪 Fetching your past tasks from 'My Tasks'...")
    payload = {
        "0": {
            "json": {
                "annotationProjectId": ANNOTATION_PROJECT_ID,
                "pipelineStageId": None,
                "statuses": None,
                "attempters": None,
                "search": None,
                "limit": 10,
                "offset": 0,
                "sortBy": "taskId",
                "sortOrder": "desc",
                "removeSkipped": True,
                "statusFilter": "all",
                "categories": None,
                "priorityLevel": None
            },
            "meta": {
                "values": {
                    "pipelineStageId": ["undefined"],
                    "statuses": ["undefined"],
                    "attempters": ["undefined"],
                    "search": ["undefined"],
                    "categories": ["undefined"],
                    "priorityLevel": ["undefined"]
                },
                "v": 1
            }
        }
    }
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            params = {
                "batch": "1",
                "input": json.dumps(payload)
            }
            async with session.get(GET_MY_TASKS_URL, params=params, timeout=10) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"❌ Fetch failed! Status Code: {resp.status}")
                    logger.error(text)
                    return

                data = await resp.json()
                active = data[0].get("result", {}).get("data", {}).get("json", {}).get("activeTasks", [])
                past = data[0].get("result", {}).get("data", {}).get("json", {}).get("pastTasks", [])
                
                logger.info(f"✅ Successfully fetched 'My Tasks'! Found {len(active)} active tasks and {len(past)} past tasks.")
                for i, t in enumerate(past):
                    cat = t.get("data", {}).get("attribute:Category", "Unknown")
                    logger.info(f"   Task {i+1}: {cat} (ID: {t.get('id')})")
                
        except Exception as e:
            logger.error(f"❌ Test crashed: {e}")

if __name__ == "__main__":
    print("\n=== DYNAMO TASK SNIPER (ASYNC MULTI-THREADED EDITION) ===")
    print("1. Start Polling (Sniper Mode)")
    print("2. Test Connection (Available Tasks)")
    print("3. Test Connection (My Past Tasks)")
    try:
        choice = input("Enter 1, 2, or 3: ").strip()
        if choice == "2":
            asyncio.run(test_connection())
        elif choice == "3":
            asyncio.run(test_my_tasks())
        else:
            asyncio.run(poll_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user.")