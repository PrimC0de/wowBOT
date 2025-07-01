# Superbank Procurement Assistant

A modern, layered chatbot architecture for Superbank Indonesia's procurement policies using OpenAI, FAISS, FastAPI, and Google Sheets integration.

---

## 🏗️ Project Structure

```
openAI/
├── main.py                     # FastAPI app entrypoint (serves the chatbot)
├── config.py                   # All configuration, constants, and environment variables
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── generate_embeddings.py      # Script for chunking and embedding knowledge files
├── credentials.json            # Google service account credentials (add to .gitignore)
│
├── data/
│   ├── _knowledge/              # Original knowledge .txt files (editable)
│   │   ├── sop.txt
│   │   ├── vmc_knowledge.txt
│   │   ├── vra_knowledge.txt
│   │   └── pengadaan_knowledge.txt
│   ├── _chunks/                 # Generated chunk files (from .txt)
│   │   ├── sopchunks.txt
│   │   ├── vmcchunks.txt
│   │   ├── vrachunks.txt
│   │   └── pengadaanchunks.txt
│   └── _index/                  # FAISS index files (from chunks)
│       ├── faiss_index_sop.index
│       ├── faiss_index_vmc.index
│       ├── faiss_index_vra.index
│       └── faiss_index_pengadaan.index
│
├── services/
│   ├── __init__.py
│   ├── openai_service.py       # OpenAI API interactions
│   ├── retrieval_service.py    # FAISS and chunk management
│   ├── chatbot_service.py      # Main chatbot orchestration
│   └── google_sheets_service.py# Google Sheets API logic
│
├── google_sheets_events.py     # High-level interface for Google Sheets (used by chatbot)
└── tests/                      # (Optional) Unit/integration tests
```

---

## 🚀 Data Flow & Pipeline

### 1. **Knowledge Preparation**

- Place your editable `.txt` knowledge files in `data/_knowledge/`.

### 2. **Chunking & Embedding Pipeline**

- Use `generate_embeddings.py` to process your knowledge files:

#### **Full Pipeline (from .txt to chunks to embeddings to index):**

```bash
python generate_embeddings.py --chunk
```

- **Step 1:** Reads each `.txt` file from `data/_knowledge/`.
- **Step 2:** Splits each file into overlapping, token-based chunks and saves as `.chunks.txt` in `data/_chunks/`.
- **Step 3:** Reads the `.chunks.txt` files, generates embeddings for each chunk, and saves/updates the FAISS index files in `data/_indexes/`.

#### **Embedding Only (from existing chunks):**

```bash
python generate_embeddings.py
```

- **Step 1:** Skips chunking, assumes `.chunks.txt` files are up-to-date.
- **Step 2:** Generates embeddings and indexes as above.

**Tip:** Use `--chunk` whenever you update your `.txt` knowledge files.

### 3. **Serving the Chatbot**

- Start the FastAPI app (does NOT re-chunk or re-embed):

```bash
.venv/bin/uvicorn main:app --reload --port 3000
```

- The chatbot loads the pre-generated `.chunks.txt` and FAISS index files for fast, scalable retrieval.

---

## 🔑 Credentials & Security

- Place `credentials.json` (Google service account) in the project root.
- **Add `credentials.json` to your `.gitignore!**
- Never commit credentials or sensitive data to version control.

---

## 📡 API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /status` - System status
- `POST /slack/events` - Slack event handler

---

## 🧪 Testing & Updating Knowledge

- Edit your `.txt` files in `data/_knowledge/` as needed.
- Run `python generate_embeddings.py --chunk` to update chunks and indexes.
- Restart your FastAPI app if needed.

---

## 🏗️ Extending the Application

- Add new document types by updating `config.py` and placing new files in `data/_knowledge/`.
- Add new features by creating new service classes in `services/`.
- Add tests in `tests/`.

---

## 📝 Best Practices

- **Keep code, data, and credentials in separate folders.**
- **Never commit credentials.json or other secrets.**
- **Regenerate chunks and indexes whenever your knowledge base changes.**
- **Monitor logs for errors and incomplete answers.**

---

## 🤝 Contributing

- Fork, branch, and submit PRs for improvements or bugfixes.
- Add tests for new features.

---

## 📝 License: -
