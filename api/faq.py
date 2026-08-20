import json
import os
import sys
from pathlib import Path

# FAQ 앱 경로 추가
faq_path = Path(__file__).parent.parent / "D23_FAQ_챗봇/stage1_local_basic"
sys.path.insert(0, str(faq_path))

from gemini import GeminiClient
from rag import answer_question

# 환경변수 로드
def load_env():
    env_file = faq_path / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

load_env()
client = GeminiClient()

def chat(message):
    """FAQ 챗봇 응답"""
    try:
        result = answer_question(message, client.generate)
        return {
            "status": result['status'],
            "answer": result['answer'],
            "source": result['source'],
            "score": result.get('score', 0)
        }
    except Exception as error:
        return {
            "status": "ERROR",
            "answer": str(error),
            "source": "없음",
            "score": 0
        }

# Vercel Functions 핸들러
async def handler(request):
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        }
    
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            message = body.get("message", "")
            
            if not message:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "message 필드가 필요합니다"})
                }
            
            result = chat(message)
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps(result, ensure_ascii=False)
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": str(e)})
            }
    
    return {
        "statusCode": 405,
        "body": json.dumps({"error": "Method not allowed"})
    }
