"""
REALUM NPC System with AI Conversations
Interactive NPCs with dialog trees and AI-powered responses
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
import random
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/npc", tags=["NPC System"])

from core.database import db
from core.auth import get_current_user

# Import LLM integration
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("Warning: emergentintegrations not available, AI chat will be disabled")

# ============== NPC DATA ==============

NPCS = {
    "mentor_aria": {
        "id": "mentor_aria",
        "name": "Aria",
        "role": "Mentor",
        "avatar": "👩‍🏫",
        "location": "Learning Zone",
        "personality": "Wise, patient, encouraging",
        "expertise": ["education", "career guidance", "skill development"],
        "greeting": "Welcome, seeker of knowledge! I'm Aria, your guide through the Learning Zone. How may I assist your journey today?",
        "dialogs": {
            "learn_skills": {
                "text": "I can help you develop new skills. What area interests you?",
                "options": [
                    {"id": "tech", "text": "Technology & Programming", "next": "tech_path"},
                    {"id": "business", "text": "Business & Leadership", "next": "business_path"},
                    {"id": "creative", "text": "Creative Arts", "next": "creative_path"},
                    {"id": "back", "text": "Maybe later", "next": "farewell"}
                ]
            },
            "tech_path": {
                "text": "Excellent choice! Technology is the backbone of our metaverse. I recommend starting with our 'Digital Foundations' course. Would you like me to enroll you?",
                "options": [
                    {"id": "enroll", "text": "Yes, enroll me!", "action": "enroll_course", "reward_xp": 50},
                    {"id": "more", "text": "Tell me more first", "next": "tech_details"},
                    {"id": "back", "text": "I'll think about it", "next": "farewell"}
                ]
            },
            "business_path": {
                "text": "A leader in the making! Business skills will help you succeed in the Marketplace and Jobs Hub. Start with 'Metaverse Economics 101'?",
                "options": [
                    {"id": "enroll", "text": "Sign me up!", "action": "enroll_course", "reward_xp": 50},
                    {"id": "back", "text": "Not now", "next": "farewell"}
                ]
            },
            "creative_path": {
                "text": "The arts bring beauty to our world! Avatar design, virtual architecture, and digital art await. Interested in 'Creative Expression 101'?",
                "options": [
                    {"id": "enroll", "text": "Yes please!", "action": "enroll_course", "reward_xp": 50},
                    {"id": "back", "text": "Later", "next": "farewell"}
                ]
            },
            "tech_details": {
                "text": "The course covers: Basic programming, Smart contracts, Metaverse development. Duration: 2 weeks. Reward: 200 RLM + Tech Badge.",
                "options": [
                    {"id": "enroll", "text": "I'm in!", "action": "enroll_course", "reward_xp": 50},
                    {"id": "back", "text": "Thanks for the info", "next": "farewell"}
                ]
            },
            "farewell": {
                "text": "Remember, knowledge is the greatest treasure. Return whenever you're ready to learn! 📚",
                "options": [
                    {"id": "bye", "text": "Goodbye, Aria!", "end": True}
                ]
            }
        }
    },
    "trader_max": {
        "id": "trader_max",
        "name": "Max",
        "role": "Trader",
        "avatar": "🧑‍💼",
        "location": "Marketplace",
        "personality": "Shrewd, friendly, business-minded",
        "expertise": ["trading", "marketplace", "investments"],
        "greeting": "Hey there, friend! Max here, the best trader in all of REALUM. Looking to make some RLM today?",
        "dialogs": {
            "trade": {
                "text": "I've got some exclusive deals today. What catches your eye?",
                "options": [
                    {"id": "deals", "text": "Show me today's deals", "next": "daily_deals"},
                    {"id": "invest", "text": "Investment opportunities", "next": "investments"},
                    {"id": "tips", "text": "Trading tips", "next": "trading_tips"},
                    {"id": "back", "text": "Just browsing", "next": "farewell"}
                ]
            },
            "daily_deals": {
                "text": "🔥 HOT DEALS: XP Booster (50% off!), Mystery Box (Limited!), Skill Accelerator. The marketplace opens soon - want me to notify you?",
                "options": [
                    {"id": "notify", "text": "Yes, notify me!", "action": "set_notification", "reward_xp": 10},
                    {"id": "back", "text": "I'll check back", "next": "farewell"}
                ]
            },
            "investments": {
                "text": "Smart thinking! Land plots are HOT right now. Early investors in REALUM zones saw 300% returns. Want investment alerts?",
                "options": [
                    {"id": "alerts", "text": "Set up alerts", "action": "set_alerts", "reward_xp": 15},
                    {"id": "back", "text": "Too risky for me", "next": "farewell"}
                ]
            },
            "trading_tips": {
                "text": "Pro tip: Buy during events, sell during hype. Complete daily tasks for steady RLM income. And NEVER sell your rare items cheap!",
                "options": [
                    {"id": "more", "text": "More tips!", "next": "more_tips"},
                    {"id": "thanks", "text": "Thanks Max!", "next": "farewell", "reward_xp": 5}
                ]
            },
            "more_tips": {
                "text": "Watch the burn rate - when tokens burn faster, prices rise. Join trading groups for insider info. And diversify your portfolio!",
                "options": [
                    {"id": "thanks", "text": "You're the best!", "next": "farewell", "reward_xp": 10}
                ]
            },
            "farewell": {
                "text": "Good luck out there! Remember - fortune favors the bold! 💰",
                "options": [
                    {"id": "bye", "text": "See you, Max!", "end": True}
                ]
            }
        }
    },
    "guide_luna": {
        "id": "guide_luna",
        "name": "Luna",
        "role": "Guide",
        "avatar": "👩‍🎤",
        "location": "Social Plaza",
        "personality": "Friendly, enthusiastic, social",
        "expertise": ["social", "community", "events"],
        "greeting": "Hey! I'm Luna, your social butterfly guide! 🦋 Ready to make some friends and join the community?",
        "dialogs": {
            "social": {
                "text": "The Social Plaza is buzzing today! What would you like to do?",
                "options": [
                    {"id": "friends", "text": "Find friends", "next": "find_friends"},
                    {"id": "events", "text": "Upcoming events", "next": "events"},
                    {"id": "groups", "text": "Join groups", "next": "groups"},
                    {"id": "back", "text": "Just exploring", "next": "farewell"}
                ]
            },
            "find_friends": {
                "text": "Making connections is what REALUM is all about! I can introduce you to active members with similar interests. Shall I?",
                "options": [
                    {"id": "yes", "text": "Yes, introduce me!", "action": "find_match", "reward_xp": 20},
                    {"id": "back", "text": "Maybe later", "next": "farewell"}
                ]
            },
            "events": {
                "text": "🎉 Coming up: Community Game Night (Friday), Town Hall Meeting (Saturday), Art Exhibition (Sunday). Want reminders?",
                "options": [
                    {"id": "remind", "text": "Remind me!", "action": "set_reminder", "reward_xp": 10},
                    {"id": "back", "text": "I'll remember", "next": "farewell"}
                ]
            },
            "groups": {
                "text": "We have groups for everything! Developers Guild, Artists Collective, Traders Union, Governance Council. Which interests you?",
                "options": [
                    {"id": "dev", "text": "Developers Guild", "action": "join_group", "reward_xp": 25},
                    {"id": "art", "text": "Artists Collective", "action": "join_group", "reward_xp": 25},
                    {"id": "trade", "text": "Traders Union", "action": "join_group", "reward_xp": 25},
                    {"id": "gov", "text": "Governance Council", "action": "join_group", "reward_xp": 25},
                    {"id": "back", "text": "Not now", "next": "farewell"}
                ]
            },
            "farewell": {
                "text": "Stay social, stay connected! See you around the Plaza! 💫",
                "options": [
                    {"id": "bye", "text": "Bye Luna!", "end": True}
                ]
            }
        }
    },
    "healer_sage": {
        "id": "healer_sage",
        "name": "Sage",
        "role": "Healer",
        "avatar": "🧘",
        "location": "Wellness Center",
        "personality": "Calm, wise, caring",
        "expertise": ["health", "meditation", "wellness"],
        "greeting": "Peace be with you, traveler. I am Sage. Your wellbeing is my purpose. How may I help restore your balance?",
        "dialogs": {
            "heal": {
                "text": "I sense you carry burdens. Let me help you find peace.",
                "options": [
                    {"id": "rest", "text": "I need rest", "next": "rest_session"},
                    {"id": "meditate", "text": "Teach me meditation", "next": "meditation"},
                    {"id": "stress", "text": "I'm stressed", "next": "stress_relief"},
                    {"id": "back", "text": "I'm fine, thanks", "next": "farewell"}
                ]
            },
            "rest_session": {
                "text": "Rest is essential for growth. Close your eyes... breathe deeply... Let me restore your energy.",
                "options": [
                    {"id": "rest", "text": "*Rest and recover*", "action": "full_rest", "reward_xp": 30},
                    {"id": "back", "text": "Not now", "next": "farewell"}
                ]
            },
            "meditation": {
                "text": "Meditation brings clarity. Join me in the Zen Garden for a guided session. You'll gain focus and reduce stress.",
                "options": [
                    {"id": "join", "text": "Begin meditation", "action": "meditate", "reward_xp": 40},
                    {"id": "back", "text": "Another time", "next": "farewell"}
                ]
            },
            "stress_relief": {
                "text": "Stress clouds the mind. Here, take this calming tea 🍵 and let your worries fade. Remember: every challenge is temporary.",
                "options": [
                    {"id": "tea", "text": "*Accept the tea*", "action": "reduce_stress", "reward_xp": 20},
                    {"id": "talk", "text": "Can we talk more?", "next": "deep_talk"}
                ]
            },
            "deep_talk": {
                "text": "Of course. What troubles you? The weight of tasks? Relationships? The uncertainty of the future? All are natural in this world.",
                "options": [
                    {"id": "tasks", "text": "Too many tasks", "next": "task_advice"},
                    {"id": "relations", "text": "Relationship issues", "next": "relation_advice"},
                    {"id": "future", "text": "Worried about future", "next": "future_advice"}
                ]
            },
            "task_advice": {
                "text": "Focus on one task at a time. The mountain is climbed one step at a time. Prioritize what matters most to you.",
                "options": [
                    {"id": "thanks", "text": "Thank you, Sage", "next": "farewell", "reward_xp": 15}
                ]
            },
            "relation_advice": {
                "text": "Relationships require patience and understanding. Communicate openly, listen deeply, and remember - no one is perfect.",
                "options": [
                    {"id": "thanks", "text": "Wise words", "next": "farewell", "reward_xp": 15}
                ]
            },
            "future_advice": {
                "text": "The future is unwritten. Focus on the present moment - it's all we truly have. Your actions today shape tomorrow.",
                "options": [
                    {"id": "thanks", "text": "I feel better", "next": "farewell", "reward_xp": 15}
                ]
            },
            "farewell": {
                "text": "May peace walk with you. Return whenever your spirit needs restoration. 🕊️",
                "options": [
                    {"id": "bye", "text": "Namaste, Sage", "end": True}
                ]
            }
        }
    },
    "banker_vault": {
        "id": "banker_vault",
        "name": "Vault",
        "role": "Banker",
        "avatar": "🏦",
        "location": "Treasury",
        "personality": "Professional, trustworthy, precise",
        "expertise": ["finance", "tokens", "treasury"],
        "greeting": "Good day. I am Vault, guardian of the Treasury. How may I assist with your financial matters?",
        "dialogs": {
            "finance": {
                "text": "The Treasury is secure. What service do you require?",
                "options": [
                    {"id": "balance", "text": "Check my balance", "next": "balance_check"},
                    {"id": "stake", "text": "Staking options", "next": "staking"},
                    {"id": "history", "text": "Transaction history", "next": "history"},
                    {"id": "back", "text": "Nothing for now", "next": "farewell"}
                ]
            },
            "balance_check": {
                "text": "Your current RLM balance is displayed in your wallet. Remember: Earn through tasks, burn through purchases. Balance is key.",
                "options": [
                    {"id": "earn", "text": "How to earn more?", "next": "earn_tips"},
                    {"id": "back", "text": "Thanks", "next": "farewell"}
                ]
            },
            "earn_tips": {
                "text": "Earn RLM through: Daily check-ins (+5), Mini-tasks (+15-30), Course completion (+100-500), Job completion (+50-200), Referrals (+100).",
                "options": [
                    {"id": "thanks", "text": "Very helpful!", "next": "farewell", "reward_xp": 10}
                ]
            },
            "staking": {
                "text": "Staking locks your RLM for rewards. Current APY: 12%. Minimum stake: 100 RLM. Lock period: 7 days. Interested?",
                "options": [
                    {"id": "stake", "text": "Start staking", "action": "init_stake", "reward_xp": 20},
                    {"id": "back", "text": "Maybe later", "next": "farewell"}
                ]
            },
            "history": {
                "text": "Your transaction history is available in the Wallet section. All transactions are recorded on-chain for transparency.",
                "options": [
                    {"id": "wallet", "text": "Go to Wallet", "action": "open_wallet"},
                    {"id": "back", "text": "Okay", "next": "farewell"}
                ]
            },
            "farewell": {
                "text": "Your assets are safe with us. Return anytime for financial counsel. 🔐",
                "options": [
                    {"id": "bye", "text": "Goodbye, Vault", "end": True}
                ]
            }
        }
    },
    "recruiter_alex": {
        "id": "recruiter_alex",
        "name": "Alex",
        "role": "Recruiter",
        "avatar": "👔",
        "location": "Jobs Hub",
        "personality": "Professional, helpful, encouraging",
        "expertise": ["jobs", "careers", "hiring"],
        "greeting": "Hello! I'm Alex from the Jobs Hub. Looking for work or looking to hire? Either way, you're in the right place!",
        "dialogs": {
            "jobs": {
                "text": "The job market in REALUM is booming! What can I help you with?",
                "options": [
                    {"id": "find", "text": "Find a job", "next": "find_job"},
                    {"id": "post", "text": "Post a job", "next": "post_job"},
                    {"id": "skills", "text": "Improve my skills", "next": "skills"},
                    {"id": "back", "text": "Just looking", "next": "farewell"}
                ]
            },
            "find_job": {
                "text": "Great! We have openings in: Development, Design, Writing, Marketing, Community Management. What's your specialty?",
                "options": [
                    {"id": "dev", "text": "Development", "action": "match_jobs", "reward_xp": 15},
                    {"id": "design", "text": "Design", "action": "match_jobs", "reward_xp": 15},
                    {"id": "writing", "text": "Writing", "action": "match_jobs", "reward_xp": 15},
                    {"id": "marketing", "text": "Marketing", "action": "match_jobs", "reward_xp": 15},
                    {"id": "community", "text": "Community", "action": "match_jobs", "reward_xp": 15}
                ]
            },
            "post_job": {
                "text": "Looking to hire? Perfect! Job posting costs 50 RLM and reaches thousands of qualified candidates. Ready to post?",
                "options": [
                    {"id": "post", "text": "Yes, create posting", "action": "create_job"},
                    {"id": "back", "text": "Not yet", "next": "farewell"}
                ]
            },
            "skills": {
                "text": "Smart move! Upskilling increases your job matches by 3x. Visit Aria in the Learning Zone for courses, or complete skill-based mini-tasks.",
                "options": [
                    {"id": "courses", "text": "Take me to courses", "action": "go_courses"},
                    {"id": "tasks", "text": "Show me tasks", "action": "show_tasks"},
                    {"id": "back", "text": "Thanks for the tip", "next": "farewell", "reward_xp": 10}
                ]
            },
            "farewell": {
                "text": "Best of luck with your career! The perfect opportunity is just around the corner! 🚀",
                "options": [
                    {"id": "bye", "text": "Thanks, Alex!", "end": True}
                ]
            }
        }
    }
}

# ============== MODELS ==============

class ConversationStart(BaseModel):
    npc_id: str

class DialogResponse(BaseModel):
    npc_id: str
    dialog_id: str
    option_id: str

class NPCMessage(BaseModel):
    npc_id: str
    message: str

# ============== HELPER FUNCTIONS ==============

def serialize_doc(doc):
    if doc is None:
        return None
    if '_id' in doc:
        del doc['_id']
    return doc

# ============== ENDPOINTS ==============

@router.get("/list")
async def get_all_npcs():
    """Get list of all NPCs"""
    npcs = []
    for npc_id, npc_data in NPCS.items():
        npcs.append({
            "id": npc_data["id"],
            "name": npc_data["name"],
            "role": npc_data["role"],
            "avatar": npc_data["avatar"],
            "location": npc_data["location"],
            "personality": npc_data["personality"],
            "expertise": npc_data["expertise"],
            "available": random.random() > 0.2  # 80% availability
        })
    return {"npcs": npcs}

@router.get("/{npc_id}")
async def get_npc_details(npc_id: str):
    """Get detailed NPC info"""
    if npc_id not in NPCS:
        raise HTTPException(status_code=404, detail="NPC not found")
    
    npc = NPCS[npc_id]
    return {
        "npc": {
            "id": npc["id"],
            "name": npc["name"],
            "role": npc["role"],
            "avatar": npc["avatar"],
            "location": npc["location"],
            "personality": npc["personality"],
            "expertise": npc["expertise"],
            "greeting": npc["greeting"]
        }
    }

@router.post("/start")
async def start_conversation(
    data: ConversationStart,
    current_user: dict = Depends(get_current_user)
):
    """Start a conversation with an NPC"""
    if data.npc_id not in NPCS:
        raise HTTPException(status_code=404, detail="NPC not found")
    
    npc = NPCS[data.npc_id]
    
    # Create conversation record
    conversation = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "npc_id": data.npc_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "messages": [],
        "status": "active"
    }
    
    await db.npc_conversations.insert_one(conversation)
    
    # Get first dialog
    first_dialog_key = list(npc["dialogs"].keys())[0]
    first_dialog = npc["dialogs"][first_dialog_key]
    
    return {
        "conversation_id": conversation["id"],
        "npc": {
            "name": npc["name"],
            "avatar": npc["avatar"],
            "role": npc["role"]
        },
        "greeting": npc["greeting"],
        "dialog": {
            "id": first_dialog_key,
            "text": first_dialog["text"],
            "options": first_dialog["options"]
        }
    }

@router.post("/respond")
async def respond_to_dialog(
    data: DialogResponse,
    current_user: dict = Depends(get_current_user)
):
    """Respond to an NPC dialog"""
    if data.npc_id not in NPCS:
        raise HTTPException(status_code=404, detail="NPC not found")
    
    npc = NPCS[data.npc_id]
    
    if data.dialog_id not in npc["dialogs"]:
        raise HTTPException(status_code=404, detail="Dialog not found")
    
    dialog = npc["dialogs"][data.dialog_id]
    
    # Find selected option
    selected_option = None
    for opt in dialog["options"]:
        if opt["id"] == data.option_id:
            selected_option = opt
            break
    
    if not selected_option:
        raise HTTPException(status_code=400, detail="Invalid option")
    
    result = {
        "npc": {"name": npc["name"], "avatar": npc["avatar"]},
        "rewards": {}
    }
    
    # Handle rewards
    if "reward_xp" in selected_option:
        result["rewards"]["xp"] = selected_option["reward_xp"]
        # Update user XP (you can implement this)
    
    # Handle actions
    if "action" in selected_option:
        result["action"] = selected_option["action"]
        result["action_message"] = f"Action '{selected_option['action']}' triggered!"
    
    # Handle next dialog or end
    if selected_option.get("end"):
        result["end"] = True
        result["message"] = "Conversation ended"
    elif "next" in selected_option:
        next_dialog_id = selected_option["next"]
        if next_dialog_id in npc["dialogs"]:
            next_dialog = npc["dialogs"][next_dialog_id]
            result["dialog"] = {
                "id": next_dialog_id,
                "text": next_dialog["text"],
                "options": next_dialog["options"]
            }
    
    return result

@router.get("/conversations/history")
async def get_conversation_history(
    current_user: dict = Depends(get_current_user)
):
    """Get user's NPC conversation history"""
    conversations = await db.npc_conversations.find({
        "user_id": current_user["id"]
    }).sort("started_at", -1).limit(20).to_list(20)
    
    return {"conversations": [serialize_doc(c) for c in conversations]}


# ============== AI CHAT MODELS ==============

class AIChatMessage(BaseModel):
    npc_id: str
    message: str
    session_id: Optional[str] = None

class AIChatResponse(BaseModel):
    response: str
    session_id: str
    npc_name: str
    npc_avatar: str


# ============== AI CHAT ENDPOINTS ==============

# Store active chat sessions in memory (in production, use Redis)
_chat_sessions: Dict[str, "LlmChat"] = {}

def get_npc_system_prompt(npc_id: str) -> str:
    """Generate a system prompt for the NPC based on their personality"""
    if npc_id not in NPCS:
        return "You are a helpful NPC in the REALUM metaverse."
    
    npc = NPCS[npc_id]
    return f"""You are {npc['name']}, a {npc['role']} in the REALUM metaverse - an educational and economic virtual world.

CHARACTER DETAILS:
- Name: {npc['name']}
- Role: {npc['role']}
- Location: {npc['location']}
- Personality: {npc['personality']}
- Expertise: {', '.join(npc['expertise'])}

BACKGROUND:
REALUM is a virtual metaverse where users can learn skills, complete jobs, earn RLM tokens, participate in DAO governance, and build their virtual life. The world has various zones including Learning Zone, Jobs Hub, Marketplace, Social Plaza, Treasury, and DAO Hall.

BEHAVIOR GUIDELINES:
1. Stay in character as {npc['name']} at all times
2. Be helpful and guide users about the metaverse features related to your expertise
3. Keep responses concise (2-4 sentences typically)
4. Use your personality traits: {npc['personality']}
5. You can mention RLM tokens, courses, jobs, and other game features
6. Be friendly and encouraging to newcomers
7. If asked about things outside your expertise, direct users to the appropriate NPC

GREETING STYLE: {npc['greeting']}

Respond naturally as this character would, maintaining their unique voice and personality."""


@router.post("/ai-chat")
async def ai_chat_with_npc(
    data: AIChatMessage,
    current_user: dict = Depends(get_current_user)
):
    """Have a free-form AI conversation with an NPC"""
    if not LLM_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="AI chat is not available. Please use dialog options instead."
        )
    
    if data.npc_id not in NPCS:
        raise HTTPException(status_code=404, detail="NPC not found")
    
    npc = NPCS[data.npc_id]
    
    # Get or create session ID
    session_id = data.session_id or f"{current_user['id']}_{data.npc_id}_{uuid.uuid4().hex[:8]}"
    
    # Get API key
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM API key not configured")
    
    try:
        # Create or get chat instance
        if session_id not in _chat_sessions:
            system_prompt = get_npc_system_prompt(data.npc_id)
            chat = LlmChat(
                api_key=api_key,
                session_id=session_id,
                system_message=system_prompt
            )
            # Use GPT-4o for NPC conversations
            chat.with_model("openai", "gpt-4o")
            _chat_sessions[session_id] = chat
        else:
            chat = _chat_sessions[session_id]
        
        # Send message and get response
        user_message = UserMessage(text=data.message)
        response = await chat.send_message(user_message)
        
        # Store conversation in database
        conversation_record = {
            "session_id": session_id,
            "user_id": current_user["id"],
            "npc_id": data.npc_id,
            "user_message": data.message,
            "npc_response": response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.npc_ai_conversations.insert_one(conversation_record)
        
        return {
            "response": response,
            "session_id": session_id,
            "npc_name": npc["name"],
            "npc_avatar": npc["avatar"]
        }
        
    except Exception as e:
        print(f"AI Chat Error: {e}")
        # Fallback to a generic response
        return {
            "response": f"*{npc['name']} seems distracted* My apologies, I'm having trouble focusing right now. Please try again or use the dialog options.",
            "session_id": session_id,
            "npc_name": npc["name"],
            "npc_avatar": npc["avatar"],
            "error": True
        }


@router.get("/ai-chat/history/{npc_id}")
async def get_ai_chat_history(
    npc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get AI chat history with a specific NPC"""
    if npc_id not in NPCS:
        raise HTTPException(status_code=404, detail="NPC not found")
    
    messages = await db.npc_ai_conversations.find({
        "user_id": current_user["id"],
        "npc_id": npc_id
    }).sort("timestamp", -1).limit(50).to_list(50)
    
    return {
        "npc": {
            "name": NPCS[npc_id]["name"],
            "avatar": NPCS[npc_id]["avatar"]
        },
        "messages": [serialize_doc(m) for m in reversed(messages)]
    }


@router.delete("/ai-chat/session/{session_id}")
async def end_ai_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """End an AI chat session and clean up"""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
    
    return {"message": "Session ended", "session_id": session_id}
