"""
Pairing System Module for WhatsApp Ban Bot
Base and credit by: LORD ZISKY
"""

import re
import hashlib
import threading
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

class PairingSystem:
    def __init__(self, db):
        self.db = db
        self.pairing_sessions = {}
        self.lock = threading.Lock()
        self.session_timeout = 300  # 5 minutes
        
    def generate_pairing_id(self, user_id: str) -> str:
        """Generate unique pairing ID"""
        timestamp = int(time.time())
        seed = f"{user_id}_{timestamp}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        pairing_id = hashlib.sha256(seed.encode()).hexdigest()[:12].upper()
        
        with self.lock:
            self.pairing_sessions[pairing_id] = {
                'user_id': user_id,
                'created_at': time.time(),
                'phone_number': None,
                'status': 'pending'
            }
        
        return pairing_id
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        # Remove any non-digit characters
        cleaned = re.sub(r'\D', '', phone_number)
        
        # Check length (minimum 10 digits for international numbers)
        if len(cleaned) < 10 or len(cleaned) > 15:
            return False
        
        # Check country code patterns
        patterns = [
            r'^1\d{10}$',  # US/Canada
            r'^44\d{10}$',  # UK
            r'^91\d{10}$',  # India
            r'^234\d{10}$',  # Nigeria
            r'^27\d{9}$',  # South Africa
            r'^33\d{9}$',  # France
            r'^49\d{10,11}$',  # Germany
            r'^7\d{10}$',  # Russia
            r'^86\d{11}$',  # China
            r'^81\d{10}$',  # Japan
            r'^82\d{10}$',  # South Korea
            r'^55\d{11}$',  # Brazil
            r'^61\d{9}$',  # Australia
        ]
        
        for pattern in patterns:
            if re.match(pattern, cleaned):
                return True
        
        # Fallback: Check if it's a valid international number with +
        if re.match(r'^\+\d{10,15}$', phone_number):
            return True
        
        return False
    
    def pair_phone_number(self, pairing_id: str, phone_number: str, notes: str = "") -> Tuple[bool, str]:
        """Pair phone number with user"""
        with self.lock:
            if pairing_id not in self.pairing_sessions:
                return False, "Pairing session expired or invalid"
            
            session = self.pairing_sessions[pairing_id]
            
            # Check session timeout
            if time.time() - session['created_at'] > self.session_timeout:
                del self.pairing_sessions[pairing_id]
                return False, "Pairing session expired"
            
            # Validate phone number
            if not self.validate_phone_number(phone_number):
                return False, "Invalid phone number format"
            
            # Format phone number
            formatted_number = self.format_phone_number(phone_number)
            
            # Check if number already paired
            existing_pairs = self.db.get_paired_accounts()
            for pair in existing_pairs:
                if pair['phone_number'] == formatted_number:
                    return False, "Phone number already paired"
            
            # Update session
            session['phone_number'] = formatted_number
            session['status'] = 'completed'
            
            # Save to database
            success = self.db.add_paired_account(
                user_id=session['user_id'],
                phone_number=formatted_number,
                notes=notes
            )
            
            if success:
                # Clean up session
                del self.pairing_sessions[pairing_id]
                
                # Generate pairing confirmation
                confirmation = self.generate_pairing_confirmation(session['user_id'], formatted_number)
                
                return True, confirmation
            else:
                return False, "Database error"
    
    def format_phone_number(self, phone_number: str) -> str:
        """Format phone number to standard international format"""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone_number)
        
        # Add country code if missing
        if not digits.startswith(('1', '7', '20', '27', '30', '31', '32', '33', '34', 
                                 '36', '39', '40', '41', '43', '44', '45', '46', '47',
                                 '48', '49', '51', '52', '53', '54', '55', '56', '57',
                                 '58', '60', '61', '62', '63', '64', '65', '66', '81',
                                 '82', '84', '86', '90', '91', '92', '93', '94', '95',
                                 '98', '211', '212', '213', '216', '218', '220', '221',
                                 '222', '223', '224', '225', '226', '227', '228', '229',
                                 '230', '231', '232', '233', '234', '235', '236', '237',
                                 '238', '239', '240', '241', '242', '243', '244', '245',
                                 '246', '247', '248', '249', '250', '251', '252', '253',
                                 '254', '255', '256', '257', '258', '260', '261', '262',
                                 '263', '264', '265', '266', '267', '268', '269', '290',
                                 '291', '297', '298', '299', '350', '351', '352', '353',
                                 '354', '355', '356', '357', '358', '359', '370', '371',
                                 '372', '373', '374', '375', '376', '377', '378', '379',
                                 '380', '381', '382', '383', '385', '386', '387', '389',
                                 '420', '421', '423', '500', '501', '502', '503', '504',
                                 '505', '506', '507', '508', '509', '590', '591', '592',
                                 '593', '594', '595', '596', '597', '598', '599', '670',
                                 '672', '673', '674', '675', '676', '677', '678', '679',
                                 '680', '681', '682', '683', '685', '686', '687', '688',
                                 '689', '690', '691', '692', '850', '852', '853', '855',
                                 '856', '880', '886', '960', '961', '962', '963', '964',
                                 '965', '966', '967', '968', '970', '971', '972', '973',
                                 '974', '975', '976', '977', '992', '993', '994', '995',
                                 '996', '998')):
            # Assume it's a local number, need country code
            # This is a simplified approach - in production you'd need better logic
            return f"1{digits}"  # Default to US/Canada
        
        return digits
    
    def generate_pairing_confirmation(self, user_id: str, phone_number: str) -> str:
        """Generate pairing confirmation message"""
        confirmation_id = hashlib.md5(f"{user_id}_{phone_number}_{int(time.time())}".encode()).hexdigest()[:8].upper()
        
        confirmation = f"""
╔══════════════════════════════════════╗
║        ✅ PAIRING CONFIRMED         ║
╚══════════════════════════════════════╝

📱 Phone Number: +{phone_number}
👤 User ID: {user_id}
🔢 Pairing ID: {confirmation_id}
⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 Reports Available: 50 (Standard Limit)

⚠️  Terms:
• This number will be used for reporting
• Do NOT use your personal WhatsApp number
• Reports are sent anonymously
• System auto-rotates proxies

📌 Note: Use /list_paired to view all paired numbers.
"""
        return confirmation
    
    def get_user_pairings(self, user_id: str) -> List[Dict]:
        """Get all pairings for a specific user"""
        return self.db.get_paired_accounts(user_id)
    
    def cleanup_expired_sessions(self):
        """Clean up expired pairing sessions"""
        with self.lock:
            current_time = time.time()
            expired = []
            
            for pairing_id, session in self.pairing_sessions.items():
                if current_time - session['created_at'] > self.session_timeout:
                    expired.append(pairing_id)
            
            for pairing_id in expired:
                del self.pairing_sessions[pairing_id]
            
            if expired:
                logging.info(f"Cleaned up {len(expired)} expired pairing sessions")
    
    def revoke_pairing(self, phone_number: str) -> bool:
        """Revoke/remove a paired number"""
        # This would mark the pairing as inactive in the database
        # Implementation depends on database structure
        return True

# Base and credit by: LORD ZISKY