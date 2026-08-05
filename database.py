"""
Database Module for WhatsApp Ban Bot
Base and credit by: LORD ZISKY
"""

import sqlite3
import json
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

class BanBotDatabase:
    def __init__(self, db_path: str = "ban_bot.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Paired accounts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS paired_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    paired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    reports_sent INTEGER DEFAULT 0,
                    last_report TIMESTAMP,
                    notes TEXT
                )
            ''')
            
            # Reported users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reported_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_number TEXT NOT NULL,
                    reporter_number TEXT,
                    report_type TEXT NOT NULL,
                    report_method TEXT NOT NULL,
                    proxy_used TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT 1,
                    response_data TEXT
                )
            ''')
            
            # Proxy statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS proxy_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_address TEXT UNIQUE NOT NULL,
                    total_requests INTEGER DEFAULT 0,
                    successful_requests INTEGER DEFAULT 0,
                    failed_requests INTEGER DEFAULT 0,
                    last_used TIMESTAMP,
                    last_status TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Bot statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_reports INTEGER DEFAULT 0,
                    successful_bans INTEGER DEFAULT 0,
                    active_proxies INTEGER DEFAULT 0,
                    paired_users INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paired_user ON paired_accounts(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reported_target ON reported_users(target_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_proxy_address ON proxy_stats(proxy_address)')
            
            conn.commit()
            conn.close()
    
    def add_paired_account(self, user_id: str, phone_number: str, notes: str = "") -> bool:
        """Add a new paired account"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO paired_accounts (user_id, phone_number, notes)
                    VALUES (?, ?, ?)
                ''', (user_id, phone_number, notes))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                logging.error(f"Failed to add paired account: {e}")
                return False
    
    def get_paired_accounts(self, user_id: str = None) -> List[Dict]:
        """Get paired accounts, optionally filtered by user_id"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('''
                    SELECT * FROM paired_accounts 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY paired_at DESC
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT * FROM paired_accounts 
                    WHERE is_active = 1
                    ORDER BY paired_at DESC
                ''')
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
    
    def increment_reports(self, phone_number: str) -> bool:
        """Increment report count for a paired account"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE paired_accounts 
                    SET reports_sent = reports_sent + 1,
                        last_report = CURRENT_TIMESTAMP
                    WHERE phone_number = ?
                ''', (phone_number,))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                logging.error(f"Failed to increment reports: {e}")
                return False
    
    def add_reported_user(self, target_number: str, reporter_number: str, 
                         report_type: str, report_method: str, 
                         proxy_used: str = None, success: bool = True, 
                         response_data: str = None) -> bool:
        """Add a reported user record"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO reported_users 
                    (target_number, reporter_number, report_type, report_method, 
                     proxy_used, success, response_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (target_number, reporter_number, report_type, report_method,
                      proxy_used, success, response_data))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                logging.error(f"Failed to add reported user: {e}")
                return False
    
    def get_reported_users(self, target_number: str = None) -> List[Dict]:
        """Get reported users, optionally filtered by target number"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if target_number:
                cursor.execute('''
                    SELECT * FROM reported_users 
                    WHERE target_number = ?
                    ORDER BY timestamp DESC
                ''', (target_number,))
            else:
                cursor.execute('''
                    SELECT * FROM reported_users 
                    ORDER BY timestamp DESC 
                    LIMIT 100
                ''')
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
    
    def update_proxy_stats(self, proxy_address: str, success: bool = True, 
                          status: str = None) -> bool:
        """Update proxy statistics"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Check if proxy exists
                cursor.execute('SELECT id FROM proxy_stats WHERE proxy_address = ?', 
                             (proxy_address,))
                exists = cursor.fetchone()
                
                if exists:
                    if success:
                        cursor.execute('''
                            UPDATE proxy_stats 
                            SET total_requests = total_requests + 1,
                                successful_requests = successful_requests + 1,
                                last_used = CURRENT_TIMESTAMP,
                                last_status = ?
                            WHERE proxy_address = ?
                        ''', (status, proxy_address))
                    else:
                        cursor.execute('''
                            UPDATE proxy_stats 
                            SET total_requests = total_requests + 1,
                                failed_requests = failed_requests + 1,
                                last_used = CURRENT_TIMESTAMP,
                                last_status = ?
                            WHERE proxy_address = ?
                        ''', (status, proxy_address))
                else:
                    if success:
                        cursor.execute('''
                            INSERT INTO proxy_stats 
                            (proxy_address, total_requests, successful_requests, 
                             last_used, last_status)
                            VALUES (?, 1, 1, CURRENT_TIMESTAMP, ?)
                        ''', (proxy_address, status))
                    else:
                        cursor.execute('''
                            INSERT INTO proxy_stats 
                            (proxy_address, total_requests, failed_requests, 
                             last_used, last_status)
                            VALUES (?, 1, 1, CURRENT_TIMESTAMP, ?)
                        ''', (proxy_address, status))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                logging.error(f"Failed to update proxy stats: {e}")
                return False
    
    def get_proxy_stats(self, limit: int = 50) -> List[Dict]:
        """Get proxy statistics"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM proxy_stats 
                WHERE is_active = 1
                ORDER BY successful_requests DESC, total_requests DESC
                LIMIT ?
            ''', (limit,))
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
    
    def get_active_proxies_count(self) -> int:
        """Get count of active proxies"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM proxy_stats WHERE is_active = 1')
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
    
    def get_bot_statistics(self) -> Dict:
        """Get overall bot statistics"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get latest stats or create new
            cursor.execute('''
                SELECT * FROM bot_stats 
                ORDER BY last_updated DESC 
                LIMIT 1
            ''')
            
            row = cursor.fetchone()
            if row:
                stats = dict(row)
            else:
                stats = {
                    'total_reports': 0,
                    'successful_bans': 0,
                    'active_proxies': self.get_active_proxies_count(),
                    'paired_users': len(self.get_paired_accounts()),
                    'last_updated': datetime.now().isoformat()
                }
            
            conn.close()
            return stats
    
    def update_bot_stats(self, total_reports: int = None, 
                        successful_bans: int = None) -> bool:
        """Update bot statistics"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO bot_stats 
                    (total_reports, successful_bans, active_proxies, paired_users)
                    VALUES (?, ?, ?, ?)
                ''', (
                    total_reports or 0,
                    successful_bans or 0,
                    self.get_active_proxies_count(),
                    len(self.get_paired_accounts())
                ))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                logging.error(f"Failed to update bot stats: {e}")
                return False

# Base and credit by: LORD ZISKY