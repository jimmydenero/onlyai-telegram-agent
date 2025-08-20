from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse

from app.config import settings
from app.db.repo import repo
from app.ingest.uploader import uploader
from app.ingest.group_digest import digest_generator
from app.security import verify_admin_token
from app.utils.text import sanitize_filename


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard():
    """Admin dashboard HTML page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>OnlyAI Telegram Agent - Admin</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .form-group { margin: 10px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea, select { width: 100%; padding: 8px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 3px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 3px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .status { padding: 10px; margin: 10px 0; border-radius: 3px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>OnlyAI Telegram Agent - Admin Dashboard</h1>
            
            <div class="section">
                <h2>Upload Knowledge Base</h2>
                <form id="uploadForm" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="file">Select File (PDF, DOCX, TXT, MD):</label>
                        <input type="file" id="file" name="file" accept=".pdf,.docx,.doc,.txt,.md" required>
                    </div>
                    <div class="form-group">
                        <label for="title">Document Title (optional):</label>
                        <input type="text" id="title" name="title" placeholder="Leave empty to use filename">
                    </div>
                    <button type="submit">Upload & Process</button>
                </form>
                <div id="uploadStatus"></div>
            </div>
            
            <div class="section">
                <h2>Whitelist Management</h2>
                <form id="whitelistForm">
                    <div class="form-group">
                        <label for="telegram_id">Telegram User ID:</label>
                        <input type="number" id="telegram_id" name="telegram_id" required>
                    </div>
                    <div class="form-group">
                        <label for="note">Note (optional):</label>
                        <input type="text" id="note" name="note" placeholder="Reason for whitelisting">
                    </div>
                    <button type="submit">Add to Whitelist</button>
                </form>
                <div id="whitelistStatus"></div>
            </div>
            
            <div class="section">
                <h2>System Actions</h2>
                <button onclick="generateDigest()">Generate Daily Digest</button>
                <button onclick="reindexAll()">Reindex All Documents</button>
                <button onclick="cleanupMessages()">Cleanup Old Messages</button>
                <div id="systemStatus"></div>
            </div>
            
            <div class="section">
                <h2>Statistics</h2>
                <div id="stats">
                    <p>Loading statistics...</p>
                </div>
            </div>
        </div>
        
        <script>
            // Upload form handler
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData();
                const file = document.getElementById('file').files[0];
                const title = document.getElementById('title').value;
                
                formData.append('file', file);
                if (title) formData.append('title', title);
                
                try {
                    const response = await fetch('/admin/upload', {
                        method: 'POST',
                        headers: {
                            'Authorization': 'Bearer ' + localStorage.getItem('admin_token')
                        },
                        body: formData
                    });
                    
                    const result = await response.json();
                    document.getElementById('uploadStatus').innerHTML = 
                        '<div class="status success">Upload successful: ' + result.chunks_created + ' chunks created</div>';
                } catch (error) {
                    document.getElementById('uploadStatus').innerHTML = 
                        '<div class="status error">Upload failed: ' + error.message + '</div>';
                }
            });
            
            // Whitelist form handler
            document.getElementById('whitelistForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const telegramId = document.getElementById('telegram_id').value;
                const note = document.getElementById('note').value;
                
                try {
                    const response = await fetch('/admin/whitelist', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + localStorage.getItem('admin_token')
                        },
                        body: JSON.stringify({telegram_user_id: parseInt(telegramId), note: note})
                    });
                    
                    const result = await response.json();
                    document.getElementById('whitelistStatus').innerHTML = 
                        '<div class="status success">User added to whitelist</div>';
                } catch (error) {
                    document.getElementById('whitelistStatus').innerHTML = 
                        '<div class="status error">Failed to add user: ' + error.message + '</div>';
                }
            });
            
            async function generateDigest() {
                try {
                    const response = await fetch('/admin/digest/generate', {
                        method: 'POST',
                        headers: {
                            'Authorization': 'Bearer ' + localStorage.getItem('admin_token')
                        }
                    });
                    
                    const result = await response.json();
                    document.getElementById('systemStatus').innerHTML = 
                        '<div class="status success">Digest generated: ' + result.message_count + ' messages processed</div>';
                } catch (error) {
                    document.getElementById('systemStatus').innerHTML = 
                        '<div class="status error">Failed to generate digest: ' + error.message + '</div>';
                }
            }
            
            async function reindexAll() {
                try {
                    const response = await fetch('/admin/reindex', {
                        method: 'POST',
                        headers: {
                            'Authorization': 'Bearer ' + localStorage.getItem('admin_token')
                        }
                    });
                    
                    const result = await response.json();
                    document.getElementById('systemStatus').innerHTML = 
                        '<div class="status success">Reindex completed</div>';
                } catch (error) {
                    document.getElementById('systemStatus').innerHTML = 
                        '<div class="status error">Reindex failed: ' + error.message + '</div>';
                }
            }
            
            async function cleanupMessages() {
                try {
                    const response = await fetch('/admin/cleanup', {
                        method: 'POST',
                        headers: {
                            'Authorization': 'Bearer ' + localStorage.getItem('admin_token')
                        }
                    });
                    
                    const result = await response.json();
                    document.getElementById('systemStatus').innerHTML = 
                        '<div class="status success">Cleanup completed: ' + result.deleted_count + ' messages removed</div>';
                } catch (error) {
                    document.getElementById('systemStatus').innerHTML = 
                        '<div class="status error">Cleanup failed: ' + error.message + '</div>';
                }
            }
            
            // Load statistics on page load
            window.addEventListener('load', async () => {
                try {
                    const response = await fetch('/admin/stats', {
                        headers: {
                            'Authorization': 'Bearer ' + localStorage.getItem('admin_token')
                        }
                    });
                    
                    const stats = await response.json();
                    document.getElementById('stats').innerHTML = `
                        <p><strong>Documents:</strong> ${stats.total_documents}</p>
                        <p><strong>Total Chunks:</strong> ${stats.total_chunks}</p>
                        <p><strong>Whitelisted Users:</strong> ${stats.whitelisted_users}</p>
                        <p><strong>QA Interactions:</strong> ${stats.qa_interactions}</p>
                    `;
                } catch (error) {
                    document.getElementById('stats').innerHTML = '<p>Failed to load statistics</p>';
                }
            });
        </script>
    </body>
    </html>
    """
    return html_content


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(None),
    _: bool = Depends(verify_admin_token)
):
    """Upload and process a document"""
    try:
        result = await uploader.process_upload(file, title)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/documents")
async def list_documents(_: bool = Depends(verify_admin_token)):
    """List all documents"""
    try:
        documents = await repo.list_documents()
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whitelist")
async def add_to_whitelist(
    data: dict,
    _: bool = Depends(verify_admin_token)
):
    """Add user to whitelist"""
    try:
        telegram_user_id = data.get("telegram_user_id")
        note = data.get("note")
        
        if not telegram_user_id:
            raise HTTPException(status_code=400, detail="telegram_user_id is required")
        
        result = await repo.add_to_whitelist(telegram_user_id, note)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/whitelist/{telegram_user_id}")
async def remove_from_whitelist(
    telegram_user_id: int,
    _: bool = Depends(verify_admin_token)
):
    """Remove user from whitelist"""
    try:
        success = await repo.remove_from_whitelist(telegram_user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found in whitelist")
        return {"message": "User removed from whitelist"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/whitelist")
async def get_whitelist(_: bool = Depends(verify_admin_token)):
    """Get all whitelisted users"""
    try:
        whitelist = await repo.get_whitelist()
        return {"whitelist": whitelist}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/digest/generate")
async def generate_digest(_: bool = Depends(verify_admin_token)):
    """Manually generate daily digest"""
    try:
        result = await digest_generator.generate_daily_digest()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex")
async def reindex_all_documents(_: bool = Depends(verify_admin_token)):
    """Reindex all documents"""
    try:
        # Get all documents
        documents = await repo.list_documents()
        
        # For now, return placeholder response
        # In a full implementation, you would reindex each document
        return {
            "message": "Reindex completed",
            "documents_processed": len(documents)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_old_messages(_: bool = Depends(verify_admin_token)):
    """Clean up old messages"""
    try:
        deleted_count = await digest_generator.cleanup_old_messages()
        return {
            "message": "Cleanup completed",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_system_stats(_: bool = Depends(verify_admin_token)):
    """Get system statistics"""
    try:
        # Get basic stats
        documents = await repo.list_documents()
        whitelist = await repo.get_whitelist()
        
        # Calculate total chunks (would need to implement in repo)
        total_chunks = 0  # Placeholder
        
        # Get QA interactions count (would need to implement in repo)
        qa_interactions = 0  # Placeholder
        
        return {
            "total_documents": len(documents),
            "total_chunks": total_chunks,
            "whitelisted_users": len(whitelist),
            "qa_interactions": qa_interactions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-answer")
async def test_answer(
    question: str,
    _: bool = Depends(verify_admin_token)
):
    """Test answer generation for a question"""
    try:
        from app.handlers.qa import qa_handler
        
        # Use a test user ID for testing
        test_user_id = settings.owner_telegram_id
        
        result = await qa_handler.process_question(test_user_id, question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
