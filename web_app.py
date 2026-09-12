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

from langchain_community.document_loaders import CSVLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

app = FastAPI(title="NutriBot RAG Web Interface", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_PATH = os.path.abspath("./data/inventario.csv")
retriever = None
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
                    # Clean up keys in case of leading/trailing whitespace
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
    global retriever
    print("Inicializando RAG y embeddings para NutriBot...")
    load_inventory_data()
    loader_csv = CSVLoader(file_path=CSV_PATH, encoding="utf-8-sig")
    documentos = loader_csv.load()
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma.from_documents(documents=documentos, embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
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

    # Special handling for greetings
    if lower_query in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey", "hola!", "hola nutribot"]:
        return ChatResponse(
            response="¡Hola! Soy **NutriBot**, tu asistente inteligente para **NutriFit Chile**. Puedo ayudarte a consultar stock, precios y disponibilidad de todos nuestros suplementos e insumos deportivos en tiempo real. ¿En qué producto te gustaría consultar hoy?",
            matches=[],
            total_found=0,
            query=query
        )

    # Special handling for asking catalog or all products
    if any(phrase in lower_query for phrase in ["todos los productos", "todo el inventario", "catalogo", "ver productos", "que productos tienes", "que tienen", "todo el stock"]):
        items = load_inventory_data()
        response_lines = ["Aquí tienes el catálogo completo actual de **NutriFit Chile**:"]
        for it in items:
            status = "🟢 En stock" if it["stock"] > 10 else "🟡 Stock limitado"
            response_lines.append(f"- **{it['producto']}**: {it['precio_formateado']} CLP ({it['stock']} unidades disponibles - {status})")
        return ChatResponse(
            response="\n".join(response_lines),
            matches=items,
            total_found=len(items),
            query=query
        )

    # RAG Vector Retrieval
    docs_encontrados = retriever.invoke(query)
    
    # Match docs back to structured items if possible
    items = load_inventory_data()
    matched_items = []
    
    for doc in docs_encontrados:
        content = doc.page_content
        # Find which item matches best
        for item in items:
            if item["producto"].lower() in content.lower() or f"id: {item['id']}" in content.lower():
                if item not in matched_items:
                    matched_items.append(item)

    if matched_items:
        response_lines = ["Basado en el inventario oficial de **NutriFit Chile**, encontré la siguiente información:"]
        for item in matched_items:
            stock_label = "🟢 Stock Disponible" if item["stock"] >= 15 else "🟡 Stock Moderado" if item["stock"] >= 5 else "🔴 Stock Crítico"
            response_lines.append(
                f"\n• **{item['producto']}**\n"
                f"  - **Precio:** {item['precio_formateado']} CLP\n"
                f"  - **Disponibilidad:** {item['stock']} unidades ({stock_label})\n"
                f"  - **Código ID:** #{item['id']}"
            )
        response_text = "\n".join(response_lines)
    elif docs_encontrados:
        response_text = "Encontré los siguientes registros en la base de datos:\n" + "\n".join([f"- {d.page_content}" for d in docs_encontrados])
    else:
        response_text = "No poseo registros sobre esa consulta en el inventario actual de NutriFit Chile. ¿Deseas consultar por Proteína Whey, Creatina o BCAA?"

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
