"""
Fallback Systems for WhatsApp Ban Bot
Base and credit by: LORD ZISKY
"""

import random
import time
import hashlib
from typing import List, Dict, Optional
import logging
from fake_useragent import UserAgent

class FallbackSystem:
    def __init__(self):
        self.ua = UserAgent()
        self.fallback_endpoints = self._get_fallback_endpoints()
        self.report_templates = self._get_report_templates()
        self.circuit_breaker = {}
        
    def _get_fallback_endpoints(self) -> List[Dict]:
        """Get fallback API endpoints and web forms"""
        return [
            # Primary endpoints
            {
                'name': 'whatsapp_web_report',
                'url': 'https://web.whatsapp.com/report',
                'method': 'POST',
                'type': 'api',
                'priority': 1
            },
            {
                'name': 'whatsapp_support_form',
                'url': 'https://support.whatsapp.com/contact/',
                'method': 'POST',
                'type': 'web',
                'priority': 2
            },
            # Fallback endpoints
            {
                'name': 'facebook_report_portal',
                'url': 'https://www.facebook.com/help/contact/209046679279097',
                'method': 'POST',
                'type': 'web',
                'priority': 3
            },
            {
                'name': 'whatsapp_business_api',
                'url': 'https://www.whatsapp.com/business/api',
                'method': 'POST',
                'type': 'api',
                'priority': 4
            },
            # Emergency endpoints
            {
                'name': 'meta_security_portal',
                'url': 'https://www.facebook.com/help/contact/209046679279097',
                'method': 'POST',
                'type': 'web',
                'priority': 5
            },
            {
                'name': 'abuse_report_api',
                'url': 'https://www.whatsapp.com/abuse',
                'method': 'POST',
                'type': 'api',
                'priority': 6
            }
        ]
    
    def _get_report_templates(self) -> List[Dict]:
        """Get various report templates to rotate"""
        return [
            {
                'reason': 'spam',
                'description': 'This account is sending bulk spam messages',
                'details': 'User is sending unsolicited promotional messages to multiple users',
                'severity': 'high'
            },
            {
                'reason': 'harassment',
                'description': 'This user is harassing and threatening others',
                'details': 'Sending threatening messages and inappropriate content',
                'severity': 'critical'
            },
            {
                'reason': 'impersonation',
                'description': 'This account is impersonating someone else',
                'details': 'Using fake identity to deceive other users',
                'severity': 'high'
            },
            {
                'reason': 'inappropriate_content',
                'description': 'Sharing violent or adult content',
                'details': 'Distributing prohibited content to minors',
                'severity': 'critical'
            },
            {
                'reason': 'scam',
                'description': 'Running financial scams and fraud',
                'details': 'Attempting to steal money through fake offers',
                'severity': 'critical'
            },
            {
                'reason': 'fake_news',
                'description': 'Spreading misinformation and fake news',
                'details': 'Distributing false information that causes harm',
                'severity': 'medium'
            },
            {
                'reason': 'underage_user',
                'description': 'User is under 16 years old',
                'details': 'Account belongs to a minor violating terms',
                'severity': 'high'
            },
            {
                'reason': 'automated_bot',
                'description': 'This is an automated bot account',
                'details': 'Mass messaging and automated behavior detected',
                'severity': 'medium'
            }
        ]
    
    def get_random_user_agent(self) -> str:
        """Get random user agent"""
        return self.ua.random
    
    def get_report_template(self, previous_reasons: List[str] = None) -> Dict:
        """Get random report template, avoiding recent reasons"""
        if previous_reasons and len(previous_reasons) >= 3:
            # Avoid using same reasons consecutively
            available = [t for t in self.report_templates if t['reason'] not in previous_reasons[-3:]]
            if available:
                return random.choice(available)
        
        return random.choice(self.report_templates)
    
    def get_fallback_endpoint(self, failed_endpoints: List[str] = None) -> Optional[Dict]:
        """Get next available endpoint based on priority and failures"""
        if failed_endpoints is None:
            failed_endpoints = []
        
        # Filter out failed endpoints and sort by priority
        available = [
            ep for ep in self.fallback_endpoints 
            if ep['name'] not in failed_endpoints
        ]
        
        if not available:
            # All endpoints failed, reset circuit breaker after cooldown
            self._reset_circuit_breaker()
            available = self.fallback_endpoints
        
        # Sort by priority and return the highest priority available
        available.sort(key=lambda x: x['priority'])
        return available[0] if available else None
    
    def generate_fake_session_data(self) -> Dict:
        """Generate fake session data for reports"""
        session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:16]
        timestamp = int(time.time())
        
        return {
            'session_id': session_id,
            'timestamp': timestamp,
            'browser_id': f"chrome_{random.randint(80, 120)}",
            'platform': random.choice(['windows', 'macos', 'android', 'ios']),
            'ip_suffix': f"{random.randint(1, 255)}.{random.randint(1, 255)}",
            'timezone_offset': random.randint(-12, 12) * 60,
            'language': random.choice(['en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE']),
            'screen_resolution': f"{random.randint(800, 3840)}x{random.randint(600, 2160)}"
        }
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker for failed endpoints"""
        current_time = time.time()
        to_remove = []
        
        for endpoint, failure_time in self.circuit_breaker.items():
            if current_time - failure_time > 300:  # 5 minute cooldown
                to_remove.append(endpoint)
        
        for endpoint in to_remove:
            del self.circuit_breaker[endpoint]
    
    def record_endpoint_failure(self, endpoint_name: str):
        """Record endpoint failure in circuit breaker"""
        self.circuit_breaker[endpoint_name] = time.time()
        logging.warning(f"Endpoint {endpoint_name} added to circuit breaker")
    
    def is_endpoint_blocked(self, endpoint_name: str) -> bool:
        """Check if endpoint is in circuit breaker"""
        if endpoint_name not in self.circuit_breaker:
            return False
        
        # Check if enough time has passed
        if time.time() - self.circuit_breaker[endpoint_name] > 300:
            del self.circuit_breaker[endpoint_name]
            return False
        
        return True
    
    def generate_headers(self, referer: str = None) -> Dict:
        """Generate realistic headers for requests"""
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin' if referer else 'cross-site',
            'Cache-Control': 'max-age=0',
        }
        
        if referer:
            headers['Referer'] = referer
        
        # Add random Chrome features
        if 'Chrome' in headers['User-Agent']:
            headers['Sec-Ch-Ua'] = '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"'
            headers['Sec-Ch-Ua-Mobile'] = '?0'
            headers['Sec-Ch-Ua-Platform'] = '"Windows"'
        
        return headers
    
    def get_emergency_proxies(self) -> List[str]:
        """Get emergency proxy list when all proxies fail"""
        # Hardcoded emergency proxies (should be updated regularly)
        emergency_proxies = [
            "104.234.146.56:8080",
            "138.197.157.44:8080",
            "159.203.61.169:8080",
            "167.99.172.58:8080",
            "206.189.237.183:8080",
            "68.183.202.76:8080",
            "142.93.143.155:8080",
            "165.227.15.70:8080",
            "134.209.29.120:8080",
            "209.97.150.167:8080"
        ]
        
        return emergency_proxies
    
    def generate_captcha_bypass_data(self) -> Dict:
        """Generate data that might help bypass simple CAPTCHAs"""
        # Note: This is for educational purposes only
        # Real CAPTCHA bypass requires more sophisticated methods
        return {
            'mouse_movements': [
                {'x': random.randint(10, 500), 'y': random.randint(10, 500), 't': random.randint(100, 1000)}
                for _ in range(random.randint(5, 15))
            ],
            'keystroke_timing': [random.randint(50, 500) for _ in range(random.randint(10, 30))],
            'scroll_depth': random.randint(100, 1000),
            'page_interaction_time': random.randint(2000, 10000),
            'cookie_acceptance': random.choice([True, False])
        }

# Base and credit by: LORD ZISKY