from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import fitz  # this is pymupdf
import io

app = FastAPI()

# Allow requests from any frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Vidora backend is running"}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Opens a PDF from raw bytes and extracts all text from every page.
    """
    text_parts = []
    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")

    for page_number in range(len(pdf_document)):
        page = pdf_document[page_number]
        page_text = page.get_text()
        text_parts.append(page_text)

    pdf_document.close()
    full_text = "\n".join(text_parts)
    return full_text.strip()


@app.post("/extract")
async def extract_content(
    file: UploadFile = File(None),
    raw_text: str = Form(None),
):
    """
    Accepts EITHER a PDF file OR raw pasted text.
    Returns the extracted/cleaned text ready for the next step (Groq).
    """

    # Case 1: User uploaded a PDF
    if file is not None:
        if not file.filename.lower().endswith(".pdf"):
            return {"error": "Only PDF files are supported right now."}

        file_bytes = await file.read()
        extracted_text = extract_text_from_pdf(file_bytes)

        if not extracted_text:
            return {"error": "Could not extract any text from this PDF. It might be a scanned image PDF."}

        return {
            "source": "pdf",
            "filename": file.filename,
            "character_count": len(extracted_text),
            "text": extracted_text,
        }

    # Case 2: User pasted raw text/notes directly
    elif raw_text is not None and raw_text.strip() != "":
        return {
            "source": "text",
            "character_count": len(raw_text),
            "text": raw_text.strip(),
        }

    # Case 3: Nothing provided
    else:
        return {"error": "Please provide either a PDF file or raw text."}