#!/usr/bin/env python3
"""
Railway/Render startup script that properly handles PORT environment variable.
"""
import os
import uvicorn

if __name__ == "__main__":
    # Get port from environment variable (Railway, Render, etc.) or default to 8000
    port = int(os.getenv("PORT", "8000"))
    
    print(f"Starting server on port {port}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
