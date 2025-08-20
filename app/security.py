from typing import Optional
from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.db.repo import repo


security = HTTPBearer()


async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """Verify admin token for protected endpoints"""
    if credentials.credentials != settings.admin_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin token"
        )
    return True


async def check_user_permission(telegram_user_id: int) -> dict:
    """Check user permissions and whitelist status"""
    # Get user from database
    user = await repo.get_user(telegram_user_id)
    
    # If user doesn't exist, create them with 'none' role
    if not user:
        user = await repo.create_user(telegram_user_id, 'none')
    
    # Check if user is owner
    if user['role'] == 'owner':
        return {
            'user_id': telegram_user_id,
            'role': 'owner',
            'allowed': True,
            'user': user
        }
    
    # Check whitelist
    is_whitelisted = await repo.is_whitelisted(telegram_user_id)
    
    return {
        'user_id': telegram_user_id,
        'role': user['role'],
        'allowed': is_whitelisted,
        'user': user
    }


async def require_owner_permission(telegram_user_id: int) -> dict:
    """Require owner permission for sensitive operations"""
    permission = await check_user_permission(telegram_user_id)
    
    if permission['role'] != 'owner':
        raise HTTPException(
            status_code=403,
            detail="Owner permission required"
        )
    
    return permission


async def require_whitelist_permission(telegram_user_id: int) -> dict:
    """Require whitelist permission for Q&A operations"""
    permission = await check_user_permission(telegram_user_id)
    
    if not permission['allowed']:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Please contact an administrator to be added to the whitelist."
        )
    
    return permission
