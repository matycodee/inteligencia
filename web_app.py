import os
import csv
import warnings
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Suppress deprecation and minor hub warnings
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from langchain_community.document_loaders import TextLoader, PyPDFLoader, CSVLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

app = FastAPI(title="NutriBot RAG Web Interface", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_PATH = os.path.abspath("./data/inventario.csv")
TXT_PATH = os.path.abspath("./data/inventario.txt")
PDF_PATH = os.path.abspath("./data/politicas.pdf")

vectorstore_instance = None
retriever = None
rag_chain = None
inventory_cache = []

def format_clp(amount: int) -> str:
    """Format integer amount as Chilean Pesos currency string."""
    return f"${amount:,.0f}".replace(",", ".")

def load_inventory_data():
    global inventory_cache
    inventory_cache = []
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    clean_row = {k.strip() if k else k: v for k, v in row.items()}
                    inventory_cache.append({
                        "id": int(clean_row.get("id", 0)),
                        "producto": clean_row.get("producto", "").strip(),
                        "stock": int(clean_row.get("stock", 0)),
                        "precio": int(clean_row.get("precio", 0)),
                        "precio_formateado": format_clp(int(clean_row.get("precio", 0)))
                    })
                except Exception as e:
                    print(f"Error parsing row {row}: {e}")
    return inventory_cache

def setup_rag():
    global retriever, vectorstore_instance
    print("Inicializando base de datos vectorial unificada (Inventario + Políticas)...")
    load_inventory_data()
    
    documentos = []
    
    # 1. Cargar inventario estructurado línea por línea para coincidencia exacta
    if os.path.exists(TXT_PATH):
        loader_txt = TextLoader(file_path=TXT_PATH, encoding="utf-8")
        docs_txt = loader_txt.load()
        from langchain_text_splitters import CharacterTextSplitter
        splitter = CharacterTextSplitter(separator="\n", chunk_size=1, chunk_overlap=0)
        documentos.extend(splitter.split_documents(docs_txt))
    elif os.path.exists(CSV_PATH):
        loader_csv = CSVLoader(file_path=CSV_PATH, encoding="utf-8-sig")
        documentos.extend(loader_csv.load())

    # 2. Cargar políticas corporativas en PDF
    if os.path.exists(PDF_PATH):
        try:
            loader_pdf = PyPDFLoader(file_path=PDF_PATH)
            documentos.extend(loader_pdf.load_and_split())
        except Exception as e:
            print(f"Advertencia al cargar PDF: {e}")

    # Vectorización con embeddings
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            embeddings = OpenAIEmbeddings()
            print("Usando OpenAI Embeddings.")
        else:
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            print("Usando HuggingFace Embeddings locales.")
    except Exception:
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    vectorstore_instance = Chroma.from_documents(documents=documentos, embedding=embeddings)
    retriever = vectorstore_instance.as_retriever(search_kwargs={"k": 1})
    print("NutriBot RAG cargado exitosamente.")

@app.on_event("startup")
def on_startup():
    setup_rag()

class ChatRequest(BaseModel):
    message: str

class ProductItem(BaseModel):
    id: int
    producto: str
    stock: int
    precio: int
    precio_formateado: str

class ChatResponse(BaseModel):
    response: str
    matches: List[dict]
    total_found: int
    query: str

@app.get("/api/inventory")
def get_inventory():
    items = load_inventory_data()
    total_stock = sum(item["stock"] for item in items)
    total_value = sum(item["stock"] * item["precio"] for item in items)
    return {
        "items": items,
        "total_products": len(items),
        "total_stock": total_stock,
        "total_valuation": total_value,
        "total_valuation_formatted": format_clp(total_value)
    }

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    global retriever
    if not retriever:
        setup_rag()
    
    query = req.message.strip()
    if not query:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    lower_query = query.lower()

    # Saludos
    if lower_query in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey", "hola!", "hola nutribot"]:
        return ChatResponse(
            response="¡Hola! Soy **NutriBot**, el asistente técnico exclusivo para los ejecutivos de soporte de **NutriFit Chile**. Puedo responder consultas de stock, precios de productos y políticas corporativas. ¿En qué puedo ayudarte?",
            matches=[],
            total_found=0,
            query=query
        )

    # Catálogo completo
    if any(phrase in lower_query for phrase in ["todos los productos", "todo el inventario", "catalogo", "ver productos", "que productos tienes", "que tienen", "todo el stock"]):
        items = load_inventory_data()
        response_lines = ["Aquí tienes el catálogo completo actual de **NutriFit Chile**:"]
        for it in items:
            status = "🟢 En stock" if it["stock"] >= 15 else "🟡 Stock limitado"
            response_lines.append(f"- **{it['producto']}**: {it['precio_formateado']} CLP ({it['stock']} unidades disponibles - {status})")
        return ChatResponse(
            response="\n".join(response_lines),
            matches=items,
            total_found=len(items),
            query=query
        )

    # Búsqueda Vectorial RAG con verificación de umbral de similitud
    results = vectorstore_instance.similarity_search_with_score(query, k=1)
    
    docs_encontrados = []
    if results:
        doc, score = results[0]
        # Distancia L2 menor a 1.25 indica relevancia semántica
        if score < 1.28:
            docs_encontrados = [doc]

    # Identificar si hay productos coincidentes
    items = load_inventory_data()
    matched_items = []
    
    for doc in docs_encontrados:
        content = doc.page_content
        for item in items:
            if item["producto"].lower() in content.lower() or f"id: {item['id']}" in content.lower():
                if item not in matched_items:
                    matched_items.append(item)

    if docs_encontrados:
        response_sections = []
        
        # Si hay texto de políticas o documentos PDF
        pdf_texts = [d.page_content.strip() for d in docs_encontrados if "Políticas" in d.page_content or "Envío" in d.page_content or "Garantía" in d.page_content or "Pago" in d.page_content or "Atención" in d.page_content]
        
        if pdf_texts:
            response_sections.append("📋 **Políticas Oficiales de NutriFit Chile:**\n" + "\n\n".join(pdf_texts))
        
        if matched_items:
            prod_lines = ["📦 **Información de Productos / Stock:**"]
            for item in matched_items:
                stock_label = "🟢 En stock" if item["stock"] >= 15 else "🟡 Stock limitado"
                prod_lines.append(f"• **{item['producto']}** (#{item['id']}): {item['precio_formateado']} CLP | Stock: {item['stock']} un. ({stock_label})")
            response_sections.append("\n".join(prod_lines))

        if not response_sections:
            response_sections.append("Basado en los registros oficiales:\n" + "\n".join([f"• {d.page_content}" for d in docs_encontrados]))

        response_text = "\n\n".join(response_sections)
    else:
        response_text = "No poseo esa información en mis registros actuales."

    return ChatResponse(
        response=response_text,
        matches=matched_items,
        total_found=len(matched_items),
        query=query
    )

# Static files mount
os.makedirs("./static", exist_ok=True)
app.mount("/", StaticFiles(directory="./static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
