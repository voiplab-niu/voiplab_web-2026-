import os
import re
import csv
import logging
from datetime import datetime
from flask import Flask, request, render_template, jsonify, Response, send_from_directory,stream_with_context
from flask_cors import CORS
from langchain_ollama import OllamaLLM, OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma

# 初始化 Flask 應用
app = Flask(__name__, static_url_path='/rag/static')
CORS(app, resources={r"/*": {"origins": "*"}})

# 設定 Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LLM & 向量嵌入
embeddings = OllamaEmbeddings(
    model="zylonai/multilingual-e5-large:latest",
    base_url="http://203.145.207.50:8000/"
)

llm = ChatOllama(
    model="cwchang/llama-3-taiwan-8b-instruct:latest",
    temperature=0.1,
    base_url="http://203.145.207.50:8000/"
)

vector_store = Chroma(
    collection_name="NIU",
    embedding_function=embeddings,
    persist_directory="./chroma_ALLe5",
    collection_metadata={"hnsw:space": "cosine"}
)

# 讀取辦法簡介文件
txt_file_path = "辦法簡介v2.txt"
pdf_files = []
if os.path.exists(txt_file_path):
    with open(txt_file_path, "r", encoding="utf-8") as file:
        pdf_files = [line for line in file if line.strip()]
else:
    logger.error("辦法簡介不存在！")

# 初始化歷史記錄CSV文件
csv_file_path = "History.csv"
if not os.path.exists(csv_file_path):
    with open(csv_file_path, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(["問題", "答案", "時間", "修改建議"])

@app.route('/rag/')
def index():
    return render_template('RAGweb.html')

@app.route('/rag/ask', methods=['POST'])
def ask():
    """處理使用者問題並返回流式回應"""
    question = request.json.get("question")
    if not question:
        return jsonify({"error": "問題內容是必須的"}), 400
    # 第一步：從辦法清單中找出最相關的文件
    messages = [{
        'role': 'user',
        'content': (
            "以下是辦法清單(包含辦法名稱和辦法簡介)：\n"
            f"{'\n '.join(pdf_files)}\n\n"
            "請仔細閱讀每個辦法名稱之後根據使用者問題，從辦法清單中找出你認為與使用者問題最相關的辦法名稱，列出三個並依相關性排名。"
            "回答檔案名稱時，需要和辦法清單中的檔案名稱一樣，請勿多字和少字。\n\n"
            "在每個檔案名稱後括號中標註你認為的相關性百分比。\n\n"
            "回答格式：\n"
            "1.辦法名稱 /XX%\n"
            "2.辦法名稱 /XX%\n"
            "3.辦法名稱 /XX%\n"
            "使用者問題：\n"
            f"{question}"
        )
    }]
    
    response = llm.invoke(messages)
    files = []
    if response and hasattr(response, 'content'):
        for line in response.content.split("\n")[:3]:  # 只取前三名
            match = re.search(r"^\d+\.\s*([^\d%]+)\s*/\d+%", line)
            if match:
                files.append(match.group(1).strip())
    # 第二步：從向量資料庫中檢索相關內容
    all_results = []
    print(files)
    if files:
        for source_file in files:
            query_embedding = embeddings.embed_query(question)
            results = vector_store.similarity_search_by_vector(
                embedding=query_embedding, 
                k=10, 
                filter={"source": f"{source_file}.pdf"}
            )
            if results:
                for doc in results:
                    all_results.append(doc.page_content)
                    
    def generate():
        """生成流式回應的生成器函數"""
        if all_results:
            query_results = "\n".join(all_results)
            messages2 = [{
                    'role': 'system',
                    'content': (
                        "你是宜蘭大學教務處的AI助手，專門提供校規相關資訊，回答要盡可能嚴謹。請遵守以下原則：\n"
                        "1. 回答風格：簡潔口語化，如同真人對話，避免機械式回應\n"
                        "2. 內容限制：僅基於提供的參考資料回答，不自行推測\n"
                        "3. 格式要求：\n"
                        "   - 直接回答問題核心，不重複問題內容\n"
                        "   - 若資訊不完整，可補充說明『建議進一步向使用者確認』\n"
                        "   - 特別注意絕對禁止提及『根據某文件』或『條文規定』等來源說明\n"
                    )
                }, {
                    'role': 'user',
                    'content': (
                        "相關資料\n"
                        f"{query_results}\n\n"
                        "使用者問題\n"
                        f"{question}\n\n"
                        "請注意：\n"
                        "- 若資料中無明確答案，請回答『目前資料中無相關規定,建議洽詢教務處人員協助』\n"
                        "- 回答結束後不需總結，直接結束回應"
                    )
                }]

            answer_content = ""
            for chunk in llm.stream(messages2):
                if chunk and hasattr(chunk, 'content'):
                    answer_content += chunk.content
                    yield chunk.content

            # 回傳來源 PDF 清單
            yield f"\n[[[SOURCE:{','.join(files)}]]]"

            # 將問題和答案儲存到 CSV 文件
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(csv_file_path, mode='a', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow([question, answer_content, timestamp, ""])
        else:
            yield "沒有查找到相關結果。"
    return Response(generate(), content_type='text/plain; charset=utf-8')
    
@app.route('/rag/modify-answer', methods=['POST'])
def modify_answer():
    """處理使用者對答案的修改建議"""
    data = request.json
    question = data.get("question")
    original_answer = data.get("original_answer")
    modified_answer = data.get("modified_answer")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not question or not original_answer or not modified_answer:
        return jsonify({"error": "缺少必要的資料"}), 400

    try:
        with open(csv_file_path, mode='a', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow([question, original_answer, timestamp, modified_answer])
        return jsonify({"message": "修改建議已提交"}), 200
    except Exception as e:
        logger.error(f"寫入 CSV 文件時出錯: {e}")
        return jsonify({"error": "提交失敗"}), 500
        
@app.route('/rag/pdfs/<filename>')
def serve_pdf(filename):
    """提供PDF文件下載"""
    return send_from_directory('static/pdfs', filename, as_attachment=False)
   
if __name__ == "__main__":
    app.run(
        host="0.0.0.0", 
        port=8081, 
        debug=True,
    )
