import json
import os
import re
import urllib.request  ###### ← 追加
import urllib.error     ###### ← 追加

# Bedrock 用クライアントは不要のため削除しました
# import boto3
# from botocore.exceptions import ClientError

# Lambda コンテキストからリージョンを抽出する関数（今回は不要だが残しています）
def extract_region_from_arn(arn):
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"

# グローバル変数
# bedrock_client = None  ###### ← 不要になったためコメントアウト
# MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")  ###### ← 不要

# ここに FastAPI の URL を設定してください（Colab 実行後の ngrok URL）
FASTAPI_URL = "https://your-ngrok-url.ngrok.io/generate"  ###### ← 変更箇所（ngrok URL に置換）

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # ユーザー情報（ログ用）
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # 入力
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])

        print("Processing message:", message)

        # 1ターンのプロンプトとしてmessageをそのまま使う（会話履歴は任意nisiteoku）
        prompt = message

        # POST 送信ペイロード 元のコードに追あわせておく
        request_payload = {
            "prompt": prompt,
            "max_new_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True
        }

        # FastAPIへPOSTリクエストを送信
        req = urllib.request.Request(
            FASTAPI_URL,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode("utf-8")
            result = json.loads(response_body)
            print("FastAPI response:", result)

        # 応答を取得
        assistant_response = result["generated_text"]  ###### ← FastAPIの戻り形式にあわせて変更

        # 会話履歴に追加
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": assistant_response})

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": conversation_history
            })
        }

    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        return {
            "statusCode": e.code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "success": False,
                "error": f"HTTP Error: {e.reason}"
            })
        }

    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "success": False,
                "error": f"URL Error: {e.reason}"
            })
        }

    except Exception as error:
        print("Unexpected Error:", str(error))
        return {
            "statusCode": 500, #元は200だが一応増やす
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
