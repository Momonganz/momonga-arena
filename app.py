# app.py
# app.py

import streamlit as st
import requests
import os
import concurrent.futures
import time
from dotenv import load_dotenv
from models_config import models

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Check if API key is available
if not OPENROUTER_API_KEY:
    st.error("❌ OPENROUTER_API_KEY is not set in your .env file. Please add it and restart the app.")
    st.stop()

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://yourdomain.com",
    "X-Title": "LLM Compare App"
}

def query_model(prompt, model_name):
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        # Add timeout to prevent hanging
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ Error: {response.status_code} - {response.text}"
    except requests.exceptions.Timeout:
        return f"❌ Timeout: Request to {model_name} timed out after 60 seconds"
    except requests.exceptions.RequestException as e:
        return f"❌ Request Error: {str(e)}"
    except Exception as e:
        return f"❌ Unexpected Error: {str(e)}"

# --- Streamlit UI ---
st.set_page_config(page_title="LLM 比較ビュー", layout="wide")
st.title("🤖 Momongaアリーナ")

# Initialize session state for conversation history
if 'conversation' not in st.session_state:
    st.session_state.conversation = []

# モデル選択
st.subheader("🔍 比較したいモデルを選んでください")
selected_model_names = st.multiselect(
    "使用するモデル", options=[m["name"] for m in models], default=[models[0]["name"]]
)

# プロンプト入力
prompt = st.text_area("💬 プロンプトを入力してください", height=150)

if st.button("送信！") and prompt and selected_model_names:
    # Add the prompt to the conversation history
    st.session_state.conversation.append({"role": "user", "content": prompt})
    
    # 選ばれたモデルに対応する実際のモデルIDを取得
    selected_models = [m for m in models if m["name"] in selected_model_names]

    # 並列処理のための関数
    def process_model(model):
        start_time = time.time()
        result = query_model(prompt, model["model"])
        elapsed_time = time.time() - start_time
        return model["name"], result, elapsed_time
    
    # 並列処理の実行
    with st.spinner("応答を取得中..."):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # すべてのモデルに対して並列でクエリを実行
            future_to_model = {executor.submit(process_model, model): model for model in selected_models}
            
            # 結果を格納する辞書
            results = {}
            elapsed_times = {}
            
            # 各モデルの列を作成
            cols = st.columns(len(selected_models))
            
            # 完了したタスクから結果を取得し、即座に表示
            for future in concurrent.futures.as_completed(future_to_model):
                model_name, response, elapsed = future.result()
                results[model_name] = response
                elapsed_times[model_name] = elapsed
                
                # Add the response to the conversation history
                st.session_state.conversation.append({"role": "assistant", "model": model_name, "content": response})
                
                # 結果の表示
                index = selected_model_names.index(model_name)
                with cols[index]:
                    st.markdown(f"### {model_name}")
                    st.markdown(f"*応答時間: {elapsed_times[model_name]:.2f}秒*")
                    st.write(response)

# Display the conversation history
st.subheader("🗨️ 会話履歴")
for entry in st.session_state.conversation:
    if entry["role"] == "user":
        st.markdown(f"**ユーザー:** {entry['content']}")
    else:
        st.markdown(f"**{entry['model']} アシスタント:** {entry['content']}")
