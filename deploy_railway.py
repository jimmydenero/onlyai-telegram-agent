#!/usr/bin/env python3
"""
Railway deployment helper script for OnlyAI Telegram Agent
"""

import os
import sys
import subprocess
import requests
import json
from pathlib import Path

def check_railway_cli():
    """Check if Railway CLI is installed"""
    try:
        result = subprocess.run(['railway', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Railway CLI is installed")
            return True
        else:
            print("❌ Railway CLI not found")
            return False
    except FileNotFoundError:
        print("❌ Railway CLI not found")
        print("Please install Railway CLI: npm install -g @railway/cli")
        return False

def check_git():
    """Check if git is available"""
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Git is available")
            return True
        else:
            print("❌ Git not found")
            return False
    except FileNotFoundError:
        print("❌ Git not found")
        return False

def check_railway_login():
    """Check if user is logged into Railway"""
    try:
        result = subprocess.run(['railway', 'whoami'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Logged into Railway")
            return True
        else:
            print("❌ Not logged into Railway")
            return False
    except Exception as e:
        print(f"❌ Railway login check failed: {e}")
        return False

def deploy_to_railway():
    """Deploy the application to Railway"""
    print("🚀 Deploying to Railway...")
    
    try:
        # Link to Railway project
        print("📎 Linking to Railway project...")
        subprocess.run(['railway', 'link'], check=True)
        
        # Deploy
        print("📦 Deploying application...")
        subprocess.run(['railway', 'up'], check=True)
        
        print("✅ Deployment successful!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        return False

def get_railway_url():
    """Get the Railway app URL"""
    try:
        result = subprocess.run(['railway', 'domain'], capture_output=True, text=True)
        if result.returncode == 0:
            domain = result.stdout.strip()
            if domain:
                url = f"https://{domain}"
                print(f"🌐 Railway app URL: {url}")
                return url
        return None
    except Exception as e:
        print(f"❌ Failed to get Railway URL: {e}")
        return None

def set_webhook(url, admin_token):
    """Set the Telegram webhook"""
    if not url or not admin_token:
        print("❌ Missing URL or admin token for webhook setup")
        return False
    
    webhook_url = f"{url}/webhook/set"
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        response = requests.post(webhook_url, headers=headers, timeout=30)
        if response.status_code == 200:
            print("✅ Webhook set successfully")
            return True
        else:
            print(f"❌ Failed to set webhook: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Webhook setup failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("🚀 Railway Deployment Helper")
    print("=" * 50)
    
    # Check prerequisites
    if not check_railway_cli():
        sys.exit(1)
    
    if not check_git():
        sys.exit(1)
    
    if not check_railway_login():
        print("Please run: railway login")
        sys.exit(1)
    
    # Deploy
    if not deploy_to_railway():
        sys.exit(1)
    
    # Get Railway URL
    railway_url = get_railway_url()
    if not railway_url:
        print("⚠️  Could not get Railway URL. Please check manually.")
        return
    
    print("=" * 50)
    print("🎉 Deployment completed!")
    print(f"🌐 Your app is available at: {railway_url}")
    print("📊 Admin dashboard:", f"{railway_url}/admin/")
    print("🔍 API docs:", f"{railway_url}/docs")
    print("=" * 50)
    
    # Ask about webhook setup
    admin_token = input("Enter your ADMIN_TOKEN to set webhook (or press Enter to skip): ").strip()
    if admin_token:
        set_webhook(railway_url, admin_token)
    
    print("\n📋 Next steps:")
    print("1. Set environment variables in Railway dashboard")
    print("2. Add PostgreSQL service and enable pgvector")
    print("3. Upload your first documents via admin dashboard")
    print("4. Add users to whitelist")
    print("5. Test the bot with /test command")

if __name__ == "__main__":
    main()
